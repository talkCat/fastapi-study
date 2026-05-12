from datetime import timedelta
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.responses import success_response
from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.user import User, UserCreate
from app.services.user import user_repository
from app.core.security import create_access_token
from app.core.config import settings
from app.core.exceptions import UnauthorizedException

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[dict[str, str]])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = user_repository.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise UnauthorizedException(detail="用户名或密码错误")
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return success_response(
        {"access_token": access_token, "token_type": "bearer"},
        message="登录成功"
    )


@router.post("/register", response_model=ApiResponse[User], status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    from app.core.exceptions import AlreadyExistsException
    existing_user = user_repository.get_by_username(db, user_in.username)
    if existing_user:
        raise AlreadyExistsException(detail="用户名已存在")
    user = user_repository.create(db, user_in)
    return success_response(user, message="注册成功", code=status.HTTP_201_CREATED)
