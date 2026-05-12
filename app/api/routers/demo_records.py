from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.core.responses import page_response, success_response
from app.db.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.demo_record import (
    DemoRecord,
    DemoRecordCreate,
    DemoRecordUpdate,
    DemoTableInitResponse,
)
from app.services.demo_record import demo_record_service, demo_record_repository

router = APIRouter(prefix="/demo-records", tags=["教学示例"])


@router.post("/init-table", response_model=ApiResponse[DemoTableInitResponse])
def init_demo_table():
    demo_record_service.init_table()
    return success_response(
        DemoTableInitResponse(
            table_name="demo_records",
            initialized=True,
            key_point="这一步相当于先把表建好；正式项目通常会用 Alembic，而不是业务接口建表。"
        ),
        message="初始化成功",
    )


@router.get("/", response_model=ApiResponse[PageData[DemoRecord]])
def list_demo_records(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    records = demo_record_service.list_records(db, skip=skip, limit=limit)
    total = demo_record_repository.count(db)
    return page_response(records, total=total, skip=skip, limit=limit, message="查询成功")


@router.get("/{record_id}", response_model=ApiResponse[DemoRecord])
def get_demo_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    record = demo_record_service.get_record(db, record_id)
    if not record:
        raise NotFoundException(detail="教学记录不存在")
    return success_response(record, message="查询成功")


@router.post("/", response_model=ApiResponse[DemoRecord], status_code=status.HTTP_201_CREATED)
def create_demo_record(
    demo_in: DemoRecordCreate,
    db: Session = Depends(get_db)
):
    existing = demo_record_repository.get_by_title(db, demo_in.title)
    if existing:
        raise AlreadyExistsException(detail="标题已存在")
    record = demo_record_service.create_record(db, demo_in)
    return success_response(record, message="创建成功", code=status.HTTP_201_CREATED)


@router.put("/{record_id}", response_model=ApiResponse[DemoRecord])
def update_demo_record(
    record_id: int,
    demo_in: DemoRecordUpdate,
    db: Session = Depends(get_db)
):
    record = demo_record_service.update_record(db, record_id, demo_in)
    if not record:
        raise NotFoundException(detail="教学记录不存在")
    return success_response(record, message="更新成功")


@router.delete("/{record_id}", response_model=ApiResponse[None])
def delete_demo_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    success = demo_record_service.delete_record(db, record_id)
    if not success:
        raise NotFoundException(detail="教学记录不存在")
    return success_response(message="删除成功")
