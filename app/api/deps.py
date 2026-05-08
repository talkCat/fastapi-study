from typing import Optional
from types import SimpleNamespace
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.user import user_repository
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException
from app.core.config import settings
from app.models.user import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    if not settings.auth_enabled:
        bypass_user = (
            db.query(UserModel)
            .filter(UserModel.is_active.is_(True))
            .order_by(UserModel.id.asc())
            .first()
        )
        if bypass_user is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="鉴权已关闭，但系统中没有可用的激活用户作为默认身份"
            )
        return SimpleNamespace(
            id=bypass_user.id,
            username=bypass_user.username,
            email=bypass_user.email,
            role="admin",
            is_active=True
        )

    if not token:
        raise UnauthorizedException(detail="缺少认证令牌")

    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException(detail="无效的认证令牌")
    username: str = payload.get("sub")
    if username is None:
        raise UnauthorizedException(detail="无效的认证令牌")
    user = user_repository.get_by_username(db, username=username)
    if user is None:
        raise UnauthorizedException(detail="用户不存在")
    return user


def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


def get_current_admin_user(current_user = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
