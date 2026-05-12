from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class BackgroundTaskRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=200, description="写入后台任务日志的备注")


class AsyncIODemoResponse(BaseModel):
    pattern: str
    recommended_for: str
    delay_ms: int
    elapsed_ms: float
    key_point: str


class ThreadpoolDemoResponse(BaseModel):
    pattern: str
    recommended_for: str
    delay_ms: int
    elapsed_ms: float
    worker_thread: str
    key_point: str


class CustomThreadpoolDemoResponse(BaseModel):
    pattern: str
    max_workers: int
    task_count: int
    delay_ms: int
    elapsed_ms: float
    worker_threads: List[str]
    unique_workers: int
    key_point: str


class SharedThreadpoolDemoResponse(BaseModel):
    pattern: str
    configured_max_workers: int
    task_count: int
    delay_ms: int
    elapsed_ms: float
    worker_threads: List[str]
    unique_workers: int
    key_point: str


class BackgroundTaskResponse(BaseModel):
    pattern: str
    status: str
    note: str
    log_path: str
    key_point: str


class ConcurrencyDemoRequest(BaseModel):
    task_delays_ms: List[int] = Field(
        default_factory=lambda: [150, 300, 450, 200],
        min_length=1,
        max_length=20,
        description="每个子任务的模拟耗时，单位毫秒"
    )
    max_concurrency: int = Field(3, ge=1, le=10, description="最大并发数")

    @field_validator("task_delays_ms")
    @classmethod
    def validate_delays(cls, values: List[int]) -> List[int]:
        if any(value <= 0 for value in values):
            raise ValueError("task_delays_ms 中的每一项都必须大于 0")
        return values


class ConcurrencyTaskResult(BaseModel):
    task_no: int
    delay_ms: int
    queue_wait_ms: float
    run_ms: float


class ConcurrencyDemoResponse(BaseModel):
    pattern: str
    max_concurrency: int
    total_tasks: int
    total_elapsed_ms: float
    recommendation: str
    results: List[ConcurrencyTaskResult]


class CpuTaskDemoRequest(BaseModel):
    iterations: int = Field(5000, ge=500, le=200000, description="CPU 计算规模，数值越大越耗 CPU")


class CpuTaskResult(BaseModel):
    prime_count: int
    checksum: int
    duration_ms: float


class CpuTaskSubmitResponse(BaseModel):
    pattern: str
    task_id: str
    status: str
    iterations: int
    poll_path: str
    key_point: str


class CpuTaskStatusResponse(BaseModel):
    pattern: str
    task_id: str
    status: str
    iterations: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[CpuTaskResult] = None
    error: Optional[str] = None
    key_point: str


class KnowledgeChunkPreview(BaseModel):
    page_no: int
    chunk_no: int
    char_count: int
    preview: str


class KnowledgeIngestSubmitResponse(BaseModel):
    pattern: str
    task_id: str
    status: str
    source_name: str
    poll_path: str
    key_point: str


class KnowledgeIngestStatusResponse(BaseModel):
    pattern: str
    task_id: str
    status: str
    stage: str
    source_name: str
    chunk_size: int
    batch_size: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_pages: int = 0
    total_chunks: int = 0
    es_documents_indexed: int = 0
    graph_nodes_written: int = 0
    graph_edges_written: int = 0
    preview_chunks: List[KnowledgeChunkPreview] = Field(default_factory=list)
    error: Optional[str] = None
    key_point: str


class BestPracticeSection(BaseModel):
    title: str
    practices: List[str]


class BestPracticeResponse(BaseModel):
    scene: str
    summary: str
    sections: List[BestPracticeSection]
