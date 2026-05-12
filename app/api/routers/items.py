from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.responses import page_response, success_response
from app.db.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.item import Item, ItemCreate, ItemUpdate, ItemCategory
from app.services.item import item_repository

router = APIRouter(prefix="/items", tags=["物品管理"])


@router.get("/", response_model=ApiResponse[PageData[Item]])
def get_items(
    category: Optional[ItemCategory] = Query(None, description="按分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if search:
        items = item_repository.search(db, keyword=search, skip=skip, limit=limit)
        total = item_repository.count_search(db, keyword=search)
    elif category:
        items = item_repository.get_by_category(db, category=category, skip=skip, limit=limit)
        total = item_repository.count_by_category(db, category=category)
    else:
        items = item_repository.get_all(db, skip=skip, limit=limit)
        total = item_repository.count(db)
    return page_response(items, total=total, skip=skip, limit=limit, message="查询成功")


@router.get("/{item_id}", response_model=ApiResponse[Item])
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    item = item_repository.get(db, item_id)
    if not item:
        raise NotFoundException(detail="物品不存在")
    return success_response(item, message="查询成功")


@router.post("/", response_model=ApiResponse[Item], status_code=status.HTTP_201_CREATED)
def create_item(
    item_in: ItemCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    item = item_repository.create(db, item_in, owner_id=current_user.id)
    return success_response(item, message="创建成功", code=status.HTTP_201_CREATED)


@router.put("/{item_id}", response_model=ApiResponse[Item])
def update_item(
    item_id: int,
    item_in: ItemUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    item = item_repository.get(db, item_id)
    if not item:
        raise NotFoundException(detail="物品不存在")
    if item.owner_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException(detail="无权限修改此物品")
    updated_item = item_repository.update(db, item_id, item_in)
    return success_response(updated_item, message="更新成功")


@router.delete("/{item_id}", response_model=ApiResponse[None])
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    item = item_repository.get(db, item_id)
    if not item:
        raise NotFoundException(detail="物品不存在")
    if item.owner_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException(detail="无权限删除此物品")
    item_repository.delete(db, item_id)
    return success_response(message="删除成功")
