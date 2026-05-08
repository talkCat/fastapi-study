import asyncio
import time
from concurrent.futures import Future, ProcessPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from threading import Lock
from threading import current_thread
from uuid import uuid4

from fastapi import BackgroundTasks
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import NotFoundException
from app.schemas.learning import (
    AsyncIODemoResponse,
    BackgroundTaskResponse,
    BestPracticeResponse,
    BestPracticeSection,
    ConcurrencyDemoResponse,
    ConcurrencyTaskResult,
    CpuTaskResult,
    CpuTaskStatusResponse,
    CpuTaskSubmitResponse,
    ThreadpoolDemoResponse,
)

LEARNING_LOG_PATH = Path("/tmp/fastapi-study-learning.log")


def _count_primes(iterations: int) -> dict:
    started_at = time.perf_counter()
    prime_count = 0
    checksum = 0

    for number in range(2, iterations + 1):
        is_prime = True
        divisor = 2
        while divisor * divisor <= number:
            if number % divisor == 0:
                is_prime = False
                break
            divisor += 1
        if is_prime:
            prime_count += 1
            checksum = (checksum + number) % 1_000_000_007

    duration_ms = (time.perf_counter() - started_at) * 1000
    return {
        "prime_count": prime_count,
        "checksum": checksum,
        "duration_ms": round(duration_ms, 2),
    }


class LearningService:
    def __init__(self):
        self._cpu_executor: ProcessPoolExecutor | None = None
        self._cpu_tasks: dict[str, dict] = {}
        self._cpu_tasks_lock = Lock()

    async def async_io_demo(self, delay_ms: int) -> AsyncIODemoResponse:
        started_at = time.perf_counter()
        await asyncio.sleep(delay_ms / 1000)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return AsyncIODemoResponse(
            pattern="async-io",
            recommended_for="数据库查询、HTTP 调用、Redis、消息队列等 IO 密集场景",
            delay_ms=delay_ms,
            elapsed_ms=round(elapsed_ms, 2),
            key_point="优先使用 async def + await，让请求在等待 IO 时把执行权还给事件循环。"
        )

    async def threadpool_demo(self, delay_ms: int) -> ThreadpoolDemoResponse:
        started_at = time.perf_counter()
        worker_thread = await run_in_threadpool(self._blocking_sleep, delay_ms)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return ThreadpoolDemoResponse(
            pattern="threadpool-offload",
            recommended_for="必须调用阻塞库时，例如传统 SDK、阻塞文件操作、旧版数据库驱动",
            delay_ms=delay_ms,
            elapsed_ms=round(elapsed_ms, 2),
            worker_thread=worker_thread,
            key_point="阻塞代码不要直接写进 async def，应该下沉到线程池，避免卡住事件循环。"
        )

    def enqueue_background_task(self, background_tasks: BackgroundTasks, note: str) -> BackgroundTaskResponse:
        background_tasks.add_task(self._write_learning_log, note)
        return BackgroundTaskResponse(
            pattern="background-task",
            status="queued",
            note=note,
            log_path=str(LEARNING_LOG_PATH),
            key_point="BackgroundTasks 适合短小的收尾任务；耗时长、可重试任务更适合独立任务队列。"
        )

    async def bounded_concurrency_demo(
        self,
        task_delays_ms: list[int],
        max_concurrency: int
    ) -> ConcurrencyDemoResponse:
        semaphore = asyncio.Semaphore(max_concurrency)
        total_started_at = time.perf_counter()

        async def run_one(task_no: int, delay_ms: int) -> ConcurrencyTaskResult:
            queued_at = time.perf_counter()
            async with semaphore:
                started_at = time.perf_counter()
                await asyncio.sleep(delay_ms / 1000)
                finished_at = time.perf_counter()
                return ConcurrencyTaskResult(
                    task_no=task_no,
                    delay_ms=delay_ms,
                    queue_wait_ms=round((started_at - queued_at) * 1000, 2),
                    run_ms=round((finished_at - started_at) * 1000, 2)
                )

        results = await asyncio.gather(
            *(run_one(task_no=index, delay_ms=delay_ms) for index, delay_ms in enumerate(task_delays_ms, start=1))
        )
        total_elapsed_ms = (time.perf_counter() - total_started_at) * 1000
        return ConcurrencyDemoResponse(
            pattern="bounded-concurrency",
            max_concurrency=max_concurrency,
            total_tasks=len(task_delays_ms),
            total_elapsed_ms=round(total_elapsed_ms, 2),
            recommendation="高并发下不要无上限并发下游依赖，优先用 Semaphore、连接池和超时控制保护数据库与外部服务。",
            results=results
        )

    def submit_cpu_task(self, iterations: int) -> CpuTaskSubmitResponse:
        task_id = uuid4().hex
        with self._cpu_tasks_lock:
            self._cpu_tasks[task_id] = {
                "pattern": "cpu-task-queue",
                "status": "queued",
                "iterations": iterations,
                "created_at": datetime.utcnow(),
                "completed_at": None,
                "result": None,
                "error": None,
                "future": None,
            }

        future = self._get_cpu_executor().submit(_count_primes, iterations)
        future.add_done_callback(partial(self._finalize_cpu_task, task_id))

        with self._cpu_tasks_lock:
            self._cpu_tasks[task_id]["future"] = future

        return CpuTaskSubmitResponse(
            pattern="cpu-task-queue",
            task_id=task_id,
            status="queued",
            iterations=iterations,
            poll_path=f"/api/v1/learning/cpu-task-demo/{task_id}",
            key_point="CPU 密集任务不要阻塞请求线程；更合理的方式是快速提交任务，再轮询或回调获取结果。"
        )

    def get_cpu_task_status(self, task_id: str) -> CpuTaskStatusResponse:
        with self._cpu_tasks_lock:
            task = self._cpu_tasks.get(task_id)
            if task is None:
                raise NotFoundException(detail="CPU 任务不存在")

            future = task.get("future")
            if task["status"] == "queued" and future is not None and future.running():
                task["status"] = "running"

            response_payload = {
                "pattern": task["pattern"],
                "task_id": task_id,
                "status": task["status"],
                "iterations": task["iterations"],
                "created_at": task["created_at"],
                "completed_at": task["completed_at"],
                "result": task["result"],
                "error": task["error"],
                "key_point": "查询接口只负责看状态，不负责等待结果；真实生产环境通常会把状态放进 Redis 或数据库。",
            }

        return CpuTaskStatusResponse(**response_payload)

    def best_practices(self) -> BestPracticeResponse:
        return BestPracticeResponse(
            scene="FastAPI 异步线程与高并发",
            summary="先区分 IO 密集还是 CPU 密集，再决定是用 async/await、线程池，还是独立任务队列/进程池。",
            sections=[
                BestPracticeSection(
                    title="1. IO 密集任务",
                    practices=[
                        "首选 async def + await，例如异步 HTTP、异步数据库驱动、Redis。",
                        "不要在 async def 中直接调用 time.sleep()、阻塞 SDK、同步数据库驱动。",
                        "一个请求里要并发多个下游 IO 时，用 asyncio.gather()，但要配合并发上限。"
                    ]
                ),
                BestPracticeSection(
                    title="2. 阻塞任务与线程池",
                    practices=[
                        "必须调用阻塞代码时，用 run_in_threadpool() 或 asyncio.to_thread() 下沉到线程池。",
                        "线程池适合短时间阻塞任务，不适合长时间 CPU 密集计算。",
                        "如果任务需要重试、持久化、失败补偿，不要只依赖 BackgroundTasks。"
                    ]
                ),
                BestPracticeSection(
                    title="3. 高并发设计",
                    practices=[
                        "限制并发数，避免数据库、第三方 API、缓存被瞬间打爆。",
                        "为下游设置超时、重试和熔断，不要让请求无限等待。",
                        "控制单次返回量，接口默认做分页、过滤、批处理，避免一次性拉全量数据。"
                    ]
                ),
                BestPracticeSection(
                    title="4. CPU 密集任务",
                    practices=[
                        "图片处理、复杂报表、机器学习推理等 CPU 密集场景不要指望 async 提升吞吐。",
                        "这类任务更适合独立 worker、进程池，或 Celery/RQ 之类的任务队列。",
                        "Web 接口应该快速返回 task_id，由后台系统异步处理。"
                    ]
                )
            ]
        )

    @staticmethod
    def _blocking_sleep(delay_ms: int) -> str:
        time.sleep(delay_ms / 1000)
        return current_thread().name

    @staticmethod
    def _write_learning_log(note: str) -> None:
        LEARNING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LEARNING_LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {note}\n")

    def shutdown(self) -> None:
        if self._cpu_executor is not None:
            self._cpu_executor.shutdown(wait=False, cancel_futures=True)
            self._cpu_executor = None

    def _get_cpu_executor(self) -> ProcessPoolExecutor:
        if self._cpu_executor is None:
            self._cpu_executor = ProcessPoolExecutor(max_workers=2)
        return self._cpu_executor

    def _finalize_cpu_task(self, task_id: str, future: Future) -> None:
        with self._cpu_tasks_lock:
            task = self._cpu_tasks.get(task_id)
            if task is None:
                return
            task["status"] = "running"

        try:
            raw_result = future.result()
            result = CpuTaskResult(**raw_result)
            status = "completed"
            error = None
        except Exception as exc:
            result = None
            status = "failed"
            error = str(exc)

        with self._cpu_tasks_lock:
            task = self._cpu_tasks.get(task_id)
            if task is None:
                return
            task["status"] = status
            task["result"] = result
            task["error"] = error
            task["completed_at"] = datetime.utcnow()


learning_service = LearningService()
