from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.routers import users, items, auth, learning, demo_records, chat_agent
from app.core.config import settings
from app.core.executors import shutdown_executors
from app.core.responses import success_response
from app.schemas.common import ErrorDetail
from app.services.learning import learning_service

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI 学习项目 - 完整的用户和物品管理API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")
app.include_router(learning.router, prefix="/api/v1")
app.include_router(demo_records.router, prefix="/api/v1")
app.include_router(chat_agent.router, prefix="/api/v1")

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    return success_response({
        "message": f"欢迎使用 {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs"
    }, message="服务启动成功")


@app.get("/health")
def health_check():
    return success_response({"status": "healthy", "debug": settings.debug}, message="健康检查通过")


@app.get("/chat")
def chat_page():
    return FileResponse(STATIC_DIR / "chat" / "index.html")


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": message,
            "data": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: Request, exc: RequestValidationError):
    errors = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
        ).model_dump()
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "请求参数校验失败",
            "data": None,
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": str(exc) if settings.debug else "服务器内部错误",
            "data": None,
        },
    )


@app.on_event("shutdown")
def shutdown_resources():
    learning_service.shutdown()
    shutdown_executors()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
