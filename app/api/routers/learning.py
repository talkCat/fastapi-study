from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, status

from app.core.responses import success_response
from app.schemas.common import ApiResponse
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
    CustomThreadpoolDemoResponse,
    KnowledgeIngestStatusResponse,
    KnowledgeIngestSubmitResponse,
    SharedThreadpoolDemoResponse,
    ThreadpoolDemoResponse,
)
from app.services.learning import learning_service

router = APIRouter(prefix="/learning", tags=["异步与高并发学习"])


@router.get("/best-practices", response_model=ApiResponse[BestPracticeResponse])
def get_best_practices():
    return success_response(learning_service.best_practices(), message="查询成功")


@router.get("/async-io-demo", response_model=ApiResponse[AsyncIODemoResponse])
async def async_io_demo(
    delay_ms: int = Query(200, ge=10, le=3000, description="模拟 IO 等待时间，单位毫秒")
):
    return success_response(await learning_service.async_io_demo(delay_ms), message="执行成功")


@router.get("/threadpool-demo", response_model=ApiResponse[ThreadpoolDemoResponse])
async def threadpool_demo(
    delay_ms: int = Query(200, ge=10, le=3000, description="模拟阻塞任务时间，单位毫秒")
):
    return success_response(await learning_service.threadpool_demo(delay_ms), message="执行成功")


@router.get("/custom-threadpool-demo", response_model=ApiResponse[CustomThreadpoolDemoResponse])
def custom_threadpool_demo(
    delay_ms: int = Query(200, ge=10, le=3000, description="每个任务的阻塞耗时，单位毫秒"),
    max_workers: int = Query(4, ge=1, le=32, description="自建线程池的最大线程数"),
    task_count: int = Query(8, ge=1, le=64, description="提交到线程池的任务数量")
):
    return success_response(
        learning_service.custom_threadpool_demo(
            delay_ms=delay_ms,
            max_workers=max_workers,
            task_count=task_count
        ),
        message="执行成功"
    )


@router.get("/shared-threadpool-demo", response_model=ApiResponse[SharedThreadpoolDemoResponse])
def shared_threadpool_demo(
    delay_ms: int = Query(200, ge=10, le=3000, description="每个任务的阻塞耗时，单位毫秒"),
    task_count: int = Query(8, ge=1, le=64, description="提交到共享线程池的任务数量")
):
    return success_response(
        learning_service.shared_threadpool_demo(
            delay_ms=delay_ms,
            task_count=task_count
        ),
        message="执行成功"
    )


@router.post("/background-task-demo", response_model=ApiResponse[BackgroundTaskResponse])
def background_task_demo(
    payload: BackgroundTaskRequest,
    background_tasks: BackgroundTasks
):
    return success_response(
        learning_service.enqueue_background_task(background_tasks, payload.note),
        message="任务已提交"
    )


@router.post("/bounded-concurrency-demo", response_model=ApiResponse[ConcurrencyDemoResponse])
async def bounded_concurrency_demo(payload: ConcurrencyDemoRequest):
    return success_response(
        await learning_service.bounded_concurrency_demo(
            task_delays_ms=payload.task_delays_ms,
            max_concurrency=payload.max_concurrency
        ),
        message="执行成功"
    )


@router.post("/cpu-task-demo", response_model=ApiResponse[CpuTaskSubmitResponse], status_code=status.HTTP_202_ACCEPTED)
def submit_cpu_task_demo(payload: CpuTaskDemoRequest):
    return success_response(
        learning_service.submit_cpu_task(payload.iterations),
        message="任务已提交",
        code=status.HTTP_202_ACCEPTED
    )


@router.post("/knowledge-ingest-demo", response_model=ApiResponse[KnowledgeIngestSubmitResponse], status_code=status.HTTP_202_ACCEPTED)
async def submit_knowledge_ingest_demo(
    file: UploadFile = File(..., description="待导入的 PDF 文件；demo 中会做轻量模拟解析"),
    chunk_size: int = Form(800, ge=200, le=4000, description="切片大小，单位字符"),
    batch_size: int = Form(4, ge=1, le=20, description="每批写 ES/图数据库的批大小")
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    source_name = file.filename or "uploaded.pdf"
    return success_response(
        learning_service.submit_knowledge_ingest_task(
            source_name=source_name,
            file_bytes=file_bytes,
            chunk_size=chunk_size,
            batch_size=batch_size
        ),
        message="任务已提交",
        code=status.HTTP_202_ACCEPTED
    )


@router.get("/knowledge-ingest-demo/{task_id}", response_model=ApiResponse[KnowledgeIngestStatusResponse])
def get_knowledge_ingest_demo_status(task_id: str):
    return success_response(learning_service.get_knowledge_ingest_status(task_id), message="查询成功")


@router.get("/cpu-task-demo/{task_id}", response_model=ApiResponse[CpuTaskStatusResponse])
def get_cpu_task_demo_status(task_id: str):
    return success_response(learning_service.get_cpu_task_status(task_id), message="查询成功")
