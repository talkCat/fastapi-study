from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.user import user_repository
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
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