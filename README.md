# FastAPI 学习项目

一个完整的 FastAPI 框架学习项目，包含用户管理和物品管理功能。

## 项目结构

```
fastapi-study/
├── app/
│   ├── __init__.py
│   ├── main.py                 # 应用入口
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # 依赖注入
│   │   └── routers/            # API路由
│   │       ├── __init__.py
│   │       ├── auth.py         # 认证接口
│   │       ├── users.py        # 用户接口
│   │       └── items.py        # 物品接口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   ├── security.py         # 安全工具
│   │   └── exceptions.py       # 自定义异常
│   ├── models/                 # SQLAlchemy模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/                # Pydantic模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   └── db/                     # 数据库层
│       ├── __init__.py
│       ├── database.py
│       └── repository.py
├── .env                        # 环境变量（本地）
├── .env.example                # 环境变量模板
├── .gitignore
├── docker-compose.yml          # 生产环境Docker配置
├── docker-compose.dev.yml      # 开发环境Docker配置
├── Dockerfile
├── Dockerfile.dev
├── Makefile
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，修改配置
```

### 3. 启动开发服务器

```bash
make dev
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 4. 使用 Docker 启动

```bash
# 开发环境
make docker-up-dev

# 生产环境
make docker-build
make docker-up
```

## 技术栈

- **FastAPI** - Web 框架
- **SQLAlchemy** - ORM
- **Pydantic** - 数据验证
- **PostgreSQL** - 数据库
- **Docker** - 容器化

## 分层架构

```
HTTP 请求
    ↓
router (API层)      - 接收请求，参数验证
    ↓
service (业务层)    - 业务逻辑处理
    ↓
repository (数据层)  - 数据库操作
    ↓
database (数据库)    - 数据持久化
```

## API 接口

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/register | 用户注册 |

### 用户接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/users/ | 获取用户列表 |
| GET | /api/v1/users/{id} | 获取单个用户 |
| POST | /api/v1/users/ | 创建用户 |
| PUT | /api/v1/users/{id} | 更新用户 |
| DELETE | /api/v1/users/{id} | 删除用户 |

### 物品接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/items/ | 获取物品列表 |
| GET | /api/v1/items/{id} | 获取单个物品 |
| POST | /api/v1/items/ | 创建物品 |
| PUT | /api/v1/items/{id} | 更新物品 |
| DELETE | /api/v1/items/{id} | 删除物品 |

## Make 命令

```bash
make install      # 安装依赖
make dev          # 开发模式运行
make run          # 生产模式运行
make docker-build # 构建 Docker 镜像
make docker-up    # 启动 Docker 容器
make docker-down  # 停止 Docker 容器
make lint         # 代码检查
make format       # 代码格式化
make clean        # 清理缓存
```

## 开发指南

### 添加新的模型

1. 在 `app/schemas/` 创建 Pydantic 模型
2. 在 `app/models/` 创建 SQLAlchemy 模型
3. 在 `app/services/` 创建业务逻辑
4. 在 `app/api/routers/` 创建 API 路由

### 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| APP_NAME | 应用名称 | FastAPI学习项目 |
| DEBUG | 调试模式 | false |
| DATABASE_URL | 数据库连接 | sqlite:///./app.db |
| SECRET_KEY | JWT密钥 | - |
| HOST | 监听地址 | 0.0.0.0 |
| PORT | 监听端口 | 8000 |

## License

MIT

## 运维指南
下载依赖
```bash
uv pip install -r requirements.txt
```
运行项目
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```