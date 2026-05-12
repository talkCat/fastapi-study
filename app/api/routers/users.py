from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.core.responses import page_response, success_response
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user import user_repository
from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/", response_model=ApiResponse[PageData[User]])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    #current_user = Depends(get_current_active_user)
):
    users = user_repository.get_all(db, skip=skip, limit=limit)
    total = user_repository.count(db)
    return page_response(users, total=total, skip=skip, limit=limit, message="查询成功")


@router.get("/{user_id}", response_model=ApiResponse[User])
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    user = user_repository.get(db, user_id)
    if not user:
        raise NotFoundException(detail="用户不存在")
    return success_response(user, message="查询成功")


@router.post("/", response_model=ApiResponse[User], status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = user_repository.get_by_username(db, user_in.username)
    if existing_user:
        raise AlreadyExistsException(detail="用户名已存在")
    existing_email = user_repository.get_by_email(db, user_in.email)
    if existing_email:
        raise AlreadyExistsException(detail="邮箱已被注册")
    user = user_repository.create(db, user_in)
    return success_response(user, message="创建成功", code=status.HTTP_201_CREATED)


@router.put("/{user_id}", response_model=ApiResponse[User])
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    user = user_repository.update(db, user_id, user_in)
    if not user:
        raise NotFoundException(detail="用户不存在")
    return success_response(user, message="更新成功")


@router.delete("/{user_id}", response_model=ApiResponse[None])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    success = user_repository.delete(db, user_id)
    if not success:
        raise NotFoundException(detail="用户不存在")
    return success_response(message="删除成功")
