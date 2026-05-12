import asyncio
import time
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from multiprocessing import get_context
from pathlib import Path
from threading import Lock
from threading import current_thread
from uuid import uuid4

from fastapi import BackgroundTasks
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import NotFoundException
from app.core.executors import get_shared_thread_pool
from app.core.config import settings
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
    CustomThreadpoolDemoResponse,
    KnowledgeChunkPreview,
    KnowledgeIngestStatusResponse,
    KnowledgeIngestSubmitResponse,
    SharedThreadpoolDemoResponse,
    ThreadpoolDemoResponse,
)

LEARNING_LOG_PATH = Path("/tmp/fastapi-study-learning.log")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def _simulate_pdf_chunking(pdf_bytes: bytes, source_name: str, chunk_size: int) -> dict:
    started_at = time.perf_counter()
    decoded_text = pdf_bytes.decode("utf-8", errors="ignore").replace("\x00", " ")
    if not decoded_text.strip():
        decoded_text = f"Simulated content extracted from {source_name}. " * 20
    decoded_text = decoded_text.replace("\r\n", "\n")

    page_candidates = [page.strip() for page in decoded_text.split("\f") if page.strip()]
    if not page_candidates:
        normalized_text = " ".join(decoded_text.split())
        page_window = max(chunk_size * 2, 400)
        page_candidates = [
            normalized_text[index:index + page_window]
            for index in range(0, len(normalized_text), page_window)
            if normalized_text[index:index + page_window].strip()
        ]

    chunks = []
    global_chunk_no = 1
    for page_no, page_text in enumerate(page_candidates, start=1):
        normalized_page_text = " ".join(page_text.split())
        for index in range(0, len(normalized_page_text), chunk_size):
            content = normalized_page_text[index:index + chunk_size].strip()
            if not content:
                continue
            chunks.append(
                {
                    "page_no": page_no,
                    "chunk_no": global_chunk_no,
                    "char_count": len(content),
                    "preview": content[:80],
                    "content": content,
                }
            )
            global_chunk_no += 1

    duration_ms = (time.perf_counter() - started_at) * 1000
    return {
        "source_name": source_name,
        "total_pages": len(page_candidates),
        "total_chunks": len(chunks),
        "chunks": chunks,
        "duration_ms": round(duration_ms, 2),
    }


class LearningService:
    def __init__(self):
        self._cpu_executor: ProcessPoolExecutor | None = None
        self._cpu_tasks: dict[str, dict] = {}
        self._cpu_tasks_lock = Lock()
        self._knowledge_tasks: dict[str, dict] = {}
        self._knowledge_tasks_lock = Lock()

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

    def custom_threadpool_demo(
        self,
        delay_ms: int,
        max_workers: int,
        task_count: int
    ) -> CustomThreadpoolDemoResponse:
        started_at = time.perf_counter()
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="learning-threadpool") as executor:
            futures = [executor.submit(self._blocking_sleep, delay_ms) for _ in range(task_count)]
            worker_threads = [future.result() for future in futures]
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return CustomThreadpoolDemoResponse(
            pattern="custom-threadpool",
            max_workers=max_workers,
            task_count=task_count,
            delay_ms=delay_ms,
            elapsed_ms=round(elapsed_ms, 2),
            worker_threads=worker_threads,
            unique_workers=len(set(worker_threads)),
            key_point="ThreadPoolExecutor 适合你自己明确知道要开多少线程的场景；它不是异步 IO 的替代品，而是阻塞任务的隔离层。"
        )

    def shared_threadpool_demo(
        self,
        delay_ms: int,
        task_count: int
    ) -> SharedThreadpoolDemoResponse:
        started_at = time.perf_counter()
        executor = get_shared_thread_pool()
        futures = [executor.submit(self._blocking_sleep, delay_ms) for _ in range(task_count)]
        worker_threads = [future.result() for future in futures]
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return SharedThreadpoolDemoResponse(
            pattern="shared-threadpool",
            configured_max_workers=settings.thread_pool_max_workers,
            task_count=task_count,
            delay_ms=delay_ms,
            elapsed_ms=round(elapsed_ms, 2),
            worker_threads=worker_threads,
            unique_workers=len(set(worker_threads)),
            key_point="共享线程池更像 Java 的 ExecutorService 单例 Bean，适合全局复用并统一控制线程数。"
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
                "created_at": _utc_now(),
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

    def submit_knowledge_ingest_task(
        self,
        source_name: str,
        file_bytes: bytes,
        chunk_size: int,
        batch_size: int
    ) -> KnowledgeIngestSubmitResponse:
        task_id = uuid4().hex
        future = get_shared_thread_pool().submit(
            self._run_knowledge_ingest_pipeline,
            task_id,
            source_name,
            file_bytes,
            chunk_size,
            batch_size
        )

        with self._knowledge_tasks_lock:
            self._knowledge_tasks[task_id] = {
                "pattern": "knowledge-ingest-pipeline",
                "status": "queued",
                "stage": "queued",
                "source_name": source_name,
                "chunk_size": chunk_size,
                "batch_size": batch_size,
                "created_at": _utc_now(),
                "completed_at": None,
                "total_pages": 0,
                "total_chunks": 0,
                "es_documents_indexed": 0,
                "graph_nodes_written": 0,
                "graph_edges_written": 0,
                "preview_chunks": [],
                "error": None,
                "future": future,
            }

        future.add_done_callback(partial(self._finalize_knowledge_ingest_task, task_id))

        return KnowledgeIngestSubmitResponse(
            pattern="knowledge-ingest-pipeline",
            task_id=task_id,
            status="queued",
            source_name=source_name,
            poll_path=f"/api/v1/learning/knowledge-ingest-demo/{task_id}",
            key_point="真实项目里上传接口只负责接收文件并返回 task_id，解析/切片/写 ES/写图谱都应放在后台流水线中。"
        )

    def get_knowledge_ingest_status(self, task_id: str) -> KnowledgeIngestStatusResponse:
        with self._knowledge_tasks_lock:
            task = self._knowledge_tasks.get(task_id)
            if task is None:
                raise NotFoundException(detail="知识入库任务不存在")
            future = task.get("future")
            if task["status"] == "queued" and future is not None and future.running():
                task["status"] = "running"
                task["stage"] = "parsing_pdf"

            response_payload = {
                "pattern": task["pattern"],
                "task_id": task_id,
                "status": task["status"],
                "stage": task["stage"],
                "source_name": task["source_name"],
                "chunk_size": task["chunk_size"],
                "batch_size": task["batch_size"],
                "created_at": task["created_at"],
                "completed_at": task["completed_at"],
                "total_pages": task["total_pages"],
                "total_chunks": task["total_chunks"],
                "es_documents_indexed": task["es_documents_indexed"],
                "graph_nodes_written": task["graph_nodes_written"],
                "graph_edges_written": task["graph_edges_written"],
                "preview_chunks": task["preview_chunks"],
                "error": task["error"],
                "key_point": "这个 demo 把知识入库拆成了解析/切片、写 ES、写图谱三个阶段；真实生产环境通常会把状态落到 Redis 或数据库。",
            }

        return KnowledgeIngestStatusResponse(**response_payload)

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
        with self._knowledge_tasks_lock:
            futures = [task_info["future"] for task_info in self._knowledge_tasks.values() if task_info.get("future") is not None]
        for future in futures:
            if not future.done():
                future.cancel()
        if self._cpu_executor is not None:
            self._cpu_executor.shutdown(wait=False, cancel_futures=True)
            self._cpu_executor = None

    def _get_cpu_executor(self) -> ProcessPoolExecutor:
        if self._cpu_executor is None:
            # Use spawn to avoid Python 3.13 warnings caused by fork() in multi-threaded processes.
            self._cpu_executor = ProcessPoolExecutor(max_workers=2, mp_context=get_context("spawn"))
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
            task["completed_at"] = _utc_now()

    def _run_knowledge_ingest_pipeline(
        self,
        task_id: str,
        source_name: str,
        file_bytes: bytes,
        chunk_size: int,
        batch_size: int
    ) -> None:
        self._update_knowledge_task(task_id, status="running", stage="parsing_pdf")
        parsed = self._get_cpu_executor().submit(
            _simulate_pdf_chunking,
            file_bytes,
            source_name,
            chunk_size
        )
        parsed_result = parsed.result()
        preview_chunks = [
            KnowledgeChunkPreview(
                page_no=chunk["page_no"],
                chunk_no=chunk["chunk_no"],
                char_count=chunk["char_count"],
                preview=chunk["preview"]
            )
            for chunk in parsed_result["chunks"][:3]
        ]
        self._update_knowledge_task(
            task_id,
            total_pages=parsed_result["total_pages"],
            total_chunks=parsed_result["total_chunks"],
            preview_chunks=preview_chunks,
        )

        self._update_knowledge_task(task_id, stage="writing_es")
        es_documents_indexed = asyncio.run(self._simulate_external_index_write(
            chunks=parsed_result["chunks"],
            batch_size=batch_size,
            max_concurrency=4,
            per_batch_delay_ms=25
        ))
        self._update_knowledge_task(task_id, es_documents_indexed=es_documents_indexed)

        self._update_knowledge_task(task_id, stage="writing_graph")
        graph_nodes_written, graph_edges_written = asyncio.run(self._simulate_graph_write(
            chunks=parsed_result["chunks"],
            batch_size=batch_size,
            max_concurrency=3,
            per_batch_delay_ms=35
        ))
        self._update_knowledge_task(
            task_id,
            graph_nodes_written=graph_nodes_written,
            graph_edges_written=graph_edges_written,
            status="completed",
            stage="completed",
            completed_at=_utc_now()
        )

    async def _simulate_external_index_write(
        self,
        chunks: list[dict],
        batch_size: int,
        max_concurrency: int,
        per_batch_delay_ms: int
    ) -> int:
        semaphore = asyncio.Semaphore(max_concurrency)
        batches = [chunks[index:index + batch_size] for index in range(0, len(chunks), batch_size)]

        async def write_one_batch(batch: list[dict]) -> int:
            async with semaphore:
                await asyncio.sleep(per_batch_delay_ms / 1000)
                return len(batch)

        results = await asyncio.gather(*(write_one_batch(batch) for batch in batches))
        return sum(results)

    async def _simulate_graph_write(
        self,
        chunks: list[dict],
        batch_size: int,
        max_concurrency: int,
        per_batch_delay_ms: int
    ) -> tuple[int, int]:
        semaphore = asyncio.Semaphore(max_concurrency)
        batches = [chunks[index:index + batch_size] for index in range(0, len(chunks), batch_size)]

        async def write_one_batch(batch: list[dict]) -> tuple[int, int]:
            async with semaphore:
                await asyncio.sleep(per_batch_delay_ms / 1000)
                nodes = len(batch)
                edges = max(0, len(batch) - 1)
                return nodes, edges

        results = await asyncio.gather(*(write_one_batch(batch) for batch in batches))
        return sum(item[0] for item in results), sum(item[1] for item in results)

    def _update_knowledge_task(self, task_id: str, **updates) -> None:
        with self._knowledge_tasks_lock:
            task = self._knowledge_tasks.get(task_id)
            if task is None:
                return
            task.update(updates)

    def _finalize_knowledge_ingest_task(self, task_id: str, future: Future) -> None:
        if future.cancelled():
            self._update_knowledge_task(
                task_id,
                status="failed",
                stage="cancelled",
                error="任务已取消",
                completed_at=_utc_now()
            )
            return
        try:
            future.result()
        except Exception as exc:
            self._update_knowledge_task(
                task_id,
                status="failed",
                stage="failed",
                error=str(exc),
                completed_at=_utc_now()
            )


learning_service = LearningService()
