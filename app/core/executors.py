from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app.core.config import settings

_shared_thread_pool: Optional[ThreadPoolExecutor] = None


def get_shared_thread_pool() -> ThreadPoolExecutor:
    global _shared_thread_pool
    if _shared_thread_pool is None:
        _shared_thread_pool = ThreadPoolExecutor(
            max_workers=settings.thread_pool_max_workers,
            thread_name_prefix="app-shared"
        )
    return _shared_thread_pool


def shutdown_executors() -> None:
    global _shared_thread_pool
    if _shared_thread_pool is not None:
        _shared_thread_pool.shutdown(wait=False, cancel_futures=True)
        _shared_thread_pool = None
