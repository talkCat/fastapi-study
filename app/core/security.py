from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings


def _get_jose():
    try:
        from jose import JWTError, jwt
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "当前环境缺少 python-jose，无法进行 JWT 签发和校验。"
            " 请执行 `pip install python-jose` 或安装 requirements.txt 中的依赖。"
        ) from exc
    return JWTError, jwt


def get_password_hash(password: str) -> str:
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return plain_password == hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    _, jwt = _get_jose()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    JWTError, jwt = _get_jose()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
