from datetime import timedelta
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user import user_repository
from app.core.security import create_access_token
from app.core.config import settings
from app.core.exceptions import AlreadyExistsException, UnauthorizedException
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/", response_model=list[User])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    #current_user = Depends(get_current_active_user)
):
    users = user_repository.get_all(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    user = user_repository.get(db, user_id)
    if not user:
        raise AlreadyExistsException(detail="用户不存在")
    return user


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
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
    return user_repository.create(db, user_in)


@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    user = user_repository.update(db, user_id, user_in)
    if not user:
        raise AlreadyExistsException(detail="用户不存在")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    success = user_repository.delete(db, user_id)
    if not success:
        raise AlreadyExistsException(detail="用户不存在")