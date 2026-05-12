from fastapi import status

from app.schemas.common import ApiResponse, PageData


def success_response(
    data=None,
    message: str = "success",
    code: int = status.HTTP_200_OK
) -> ApiResponse:
    return ApiResponse(code=code, message=message, data=data)


def page_response(
    items: list,
    total: int,
    skip: int,
    limit: int,
    message: str = "success",
    code: int = status.HTTP_200_OK
) -> ApiResponse[PageData]:
    return ApiResponse(
        code=code,
        message=message,
        data=PageData(items=items, total=total, skip=skip, limit=limit),
    )
