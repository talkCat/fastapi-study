from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

Base = declarative_base()
_engine = None
_session_factory: Optional[sessionmaker] = None


def _get_connect_args() -> dict:
    if "mysql" in settings.database_url:
        return {"charset": "utf8mb4"}
    if "sqlite" in settings.database_url:
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_driver() -> None:
    if "sqlite" not in settings.database_url:
        return
    try:
        import sqlite3  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "当前 Python 环境缺少 sqlite3 驱动，无法使用默认的 SQLite 数据库。"
            " 处理方式：1. 安装带 sqlite3 模块的 Python；"
            " 2. 或在 .env 中把 DATABASE_URL 改成 MySQL 连接串，参考 .env.example。"
        ) from exc


def get_engine():
    global _engine
    if _engine is None:
        _ensure_sqlite_driver()
        _engine = create_engine(
            settings.database_url,
            connect_args=_get_connect_args(),
            echo=settings.debug,
            pool_pre_ping=True,
            pool_recycle=3600
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _session_factory


def get_db():
    try:
        db = get_session_factory()()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc
    try:
        yield db
    finally:
        db.close()
