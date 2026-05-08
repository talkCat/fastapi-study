from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import users, items, auth, learning
from app.core.config import settings
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


@app.get("/")
def root():
    return {
        "message": f"欢迎使用 {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "debug": settings.debug}


@app.on_event("shutdown")
def shutdown_resources():
    learning_service.shutdown()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
