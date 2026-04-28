from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "资源已存在"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "未授权"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "禁止访问"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationException(HTTPException):
    def __init__(self, detail: str = "验证失败"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)