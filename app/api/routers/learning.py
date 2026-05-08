from fastapi import APIRouter, BackgroundTasks, Query, status

from app.schemas.learning import (
    AsyncIODemoResponse,
    BackgroundTaskRequest,
    BackgroundTaskResponse,
    BestPracticeResponse,
    ConcurrencyDemoRequest,
    ConcurrencyDemoResponse,
    CpuTaskDemoRequest,
    CpuTaskStatusResponse,
    CpuTaskSubmitResponse,
    ThreadpoolDemoResponse,
)
from app.services.learning import learning_service

router = APIRouter(prefix="/learning", tags=["异步与高并发学习"])


@router.get("/best-practices", response_model=BestPracticeResponse)
def get_best_practices():
    return learning_service.best_practices()


@router.get("/async-io-demo", response_model=AsyncIODemoResponse)
async def async_io_demo(
    delay_ms: int = Query(200, ge=10, le=3000, description="模拟 IO 等待时间，单位毫秒")
):
    return await learning_service.async_io_demo(delay_ms)


@router.get("/threadpool-demo", response_model=ThreadpoolDemoResponse)
async def threadpool_demo(
    delay_ms: int = Query(200, ge=10, le=3000, description="模拟阻塞任务时间，单位毫秒")
):
    return await learning_service.threadpool_demo(delay_ms)


@router.post("/background-task-demo", response_model=BackgroundTaskResponse)
def background_task_demo(
    payload: BackgroundTaskRequest,
    background_tasks: BackgroundTasks
):
    return learning_service.enqueue_background_task(background_tasks, payload.note)


@router.post("/bounded-concurrency-demo", response_model=ConcurrencyDemoResponse)
async def bounded_concurrency_demo(payload: ConcurrencyDemoRequest):
    return await learning_service.bounded_concurrency_demo(
        task_delays_ms=payload.task_delays_ms,
        max_concurrency=payload.max_concurrency
    )


@router.post("/cpu-task-demo", response_model=CpuTaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_cpu_task_demo(payload: CpuTaskDemoRequest):
    return learning_service.submit_cpu_task(payload.iterations)


@router.get("/cpu-task-demo/{task_id}", response_model=CpuTaskStatusResponse)
def get_cpu_task_demo_status(task_id: str):
    return learning_service.get_cpu_task_status(task_id)
