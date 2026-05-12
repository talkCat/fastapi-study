from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(..., description="业务状态码，通常与 HTTP 状态码保持一致")
    message: str = Field(..., description="响应说明")
    data: T | None = Field(default=None, description="响应数据")


class ErrorDetail(BaseModel):
    field: str = Field(..., description="出错字段")
    message: str = Field(..., description="错误信息")


class ErrorResponse(BaseModel):
    code: int = Field(..., description="业务状态码，通常与 HTTP 状态码保持一致")
    message: str = Field(..., description="错误说明")
    data: None = Field(default=None, description="错误响应固定为 null")
    errors: list[ErrorDetail] | None = Field(default=None, description="字段级错误明细")


class PageData(BaseModel, Generic[T]):
    items: list[T] = Field(..., description="当前页数据")
    total: int = Field(..., ge=0, description="总记录数")
    skip: int = Field(..., ge=0, description="跳过记录数")
    limit: int = Field(..., ge=1, description="每页数量")
