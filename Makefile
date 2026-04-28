.PHONY: help install dev run test docker-build docker-up docker-down lint format clean

help:
	@echo "FastAPI 项目快捷命令"
	@echo ""
	@echo "可用命令:"
	@echo "  make install      - 安装依赖"
	@echo "  make dev          - 开发模式运行"
	@echo "  make run          - 生产模式运行"
	@echo "  make test         - 运行测试"
	@echo "  make docker-build - 构建 Docker 镜像"
	@echo "  make docker-up    - 启动 Docker 容器"
	@echo "  make docker-down  - 停止 Docker 容器"
	@echo "  make lint         - 代码检查"
	@echo "  make format       - 代码格式化"
	@echo "  make clean        - 清理缓存文件"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	pytest -v

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-up-dev:
	docker-compose -f docker-compose.dev.yml up -d

docker-down:
	docker-compose down

docker-down-dev:
	docker-compose -f docker-compose.dev.yml down

lint:
	ruff check .

format:
	ruff format .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -f app.db
	rm -rf .pytest_cache