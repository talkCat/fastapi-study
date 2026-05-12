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
│   │       ├── demo_records.py # 教学示例：controller/service/dao 全流程
│   │       ├── learning.py     # 异步与高并发学习接口
│   │       ├── users.py        # 用户接口
│   │       └── items.py        # 物品接口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   ├── executors.py        # 共享线程池/执行器
│   │   ├── security.py         # 安全工具
│   │   └── exceptions.py       # 自定义异常
│   ├── models/                 # SQLAlchemy模型
│   │   ├── __init__.py
│   │   ├── demo_record.py
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/                # Pydantic模型
│   │   ├── __init__.py
│   │   ├── demo_record.py
│   │   ├── learning.py
│   │   ├── user.py
│   │   └── item.py
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── demo_record.py
│   │   ├── learning.py
│   │   ├── user.py
│   │   └── item.py
│   └── db/                     # 数据库层
│       ├── __init__.py
│       ├── database.py
│       └── repository.py
├── docs/
│   ├── async_concurrency_guide.md
│   └── python_syntax_notes.md
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

## 统一返回体

项目现在提供了通用 RESTful 返回结构，风格上接近 Java 项目里常见的 `Result<T>`。

成功响应：

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "id": 1
  }
}
```

分页响应：

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "items": [],
    "total": 0,
    "skip": 0,
    "limit": 20
  }
}
```

错误响应：

```json
{
  "code": 404,
  "message": "教学记录不存在",
  "data": null
}
```

校验失败响应：

```json
{
  "code": 422,
  "message": "请求参数校验失败",
  "data": null,
  "errors": [
    {
      "field": "body.title",
      "message": "Field required"
    }
  ]
}
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

### 教学示例接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/demo-records/init-table | 初始化教学表 |
| GET | /api/v1/demo-records/ | 查询教学记录列表 |
| GET | /api/v1/demo-records/{id} | 查询单条教学记录 |
| POST | /api/v1/demo-records/ | 新增教学记录 |
| PUT | /api/v1/demo-records/{id} | 更新教学记录 |
| DELETE | /api/v1/demo-records/{id} | 删除教学记录 |

### 异步与高并发学习接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/learning/best-practices | 查看异步与高并发最佳实践总结 |
| GET | /api/v1/learning/async-io-demo | 演示 IO 密集任务的异步写法 |
| GET | /api/v1/learning/threadpool-demo | 演示阻塞任务如何下沉线程池 |
| GET | /api/v1/learning/custom-threadpool-demo | 演示按需创建 ThreadPoolExecutor |
| GET | /api/v1/learning/shared-threadpool-demo | 演示共享 ThreadPoolExecutor 的 Java 风格写法 |
| POST | /api/v1/learning/background-task-demo | 演示请求返回后执行短后台任务 |
| POST | /api/v1/learning/bounded-concurrency-demo | 演示受控并发与限流 |
| POST | /api/v1/learning/cpu-task-demo | 提交 CPU 密集任务并立即返回 task_id |
| GET | /api/v1/learning/cpu-task-demo/{task_id} | 查询 CPU 密集任务状态与结果 |
| POST | /api/v1/learning/knowledge-ingest-demo | 演示 PDF 知识入库任务的提交 |
| GET | /api/v1/learning/knowledge-ingest-demo/{task_id} | 查询知识入库流水线的阶段状态 |

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

### Java 风格全流程学习建议

如果你想按 Java 的 `controller -> service -> dao` 思路理解 FastAPI，可以直接读这组教学示例：

- router/controller：`app/api/routers/demo_records.py`
- service：`app/services/demo_record.py`
- dao/repository：`DemoRecordRepository`
- model：`app/models/demo_record.py`
- dto/schema：`app/schemas/demo_record.py`
- 查库流程与统一返回体学习文档：`docs/database_query_and_response_guide.md`

推荐学习顺序：

1. 先确保数据库可用：
   使用支持 `sqlite3` 的 Python，或在 `.env` 中配置 MySQL `DATABASE_URL`
2. 再调用 `POST /api/v1/demo-records/init-table` 初始化表
3. 然后调用 `POST /api/v1/demo-records/` 新建一条记录
4. 再查看 `GET /api/v1/demo-records/{id}`、`PUT`、`DELETE`
5. 对照代码看请求是如何从 router 流到 service，再流到 repository 的

对应测试：

- `tests/test_demo_record_flow.py`
- 运行命令：`python -m unittest tests.test_demo_record_flow`

### 异步与高并发学习建议

- 先看 [docs/async_concurrency_guide.md](docs/async_concurrency_guide.md)
- 再看 [docs/database_query_and_response_guide.md](docs/database_query_and_response_guide.md)，理解请求怎么查库、怎么包装统一返回体
- 遇到语法障碍时，对照 [docs/python_syntax_notes.md](docs/python_syntax_notes.md)
- 再通过 `/docs` 调用 `learning` 分组下的 11 个示例接口
- 重点对比 `async-io-demo` 和 `threadpool-demo` 的适用场景
- 通过 `shared-threadpool-demo` 观察共享 `ThreadPoolExecutor` 的 Java 风格写法
- 通过 `custom-threadpool-demo` 对比按需创建线程池的效果
- 理解 `bounded-concurrency-demo` 中 `max_concurrency` 的作用，再迁移到真实数据库/第三方 API 调用中
- 体验 `knowledge-ingest-demo`，把“切片 -> ES -> 图谱”的混合型任务拆成后台流水线
- 最后体验 `cpu-task-demo` 的“提交后轮询”模式，理解为什么 CPU 密集任务不应阻塞请求链路

### 学习模块测试

- 学习模块接口测试文件：`tests/test_learning_endpoints.py`
- 运行命令：`python -m unittest tests.test_learning_endpoints`

### 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| APP_NAME | 应用名称 | FastAPI学习项目 |
| DEBUG | 调试模式 | false |
| AUTH_ENABLED | 是否启用接口鉴权 | true |
| THREAD_POOL_MAX_WORKERS | 共享线程池最大线程数 | 8 |
| DATABASE_URL | 数据库连接 | mysql+pymysql://root:123456@10.20.40.26:3306/fastapi_study?charset=utf8mb4 |
| SECRET_KEY | JWT密钥 | - |
| HOST | 监听地址 | 0.0.0.0 |
| PORT | 监听端口 | 8000 |

鉴权开关说明：

- `AUTH_ENABLED=true`：按 JWT 正常鉴权
- `AUTH_ENABLED=false`：跳过 JWT 校验，受保护接口会使用系统中首个激活用户作为默认身份执行，并以管理员权限视角放行
- `THREAD_POOL_MAX_WORKERS`：控制共享线程池的线程数量，适合像 Java 那样统一管理执行器
- `DATABASE_URL`：默认按仓库里的 MySQL 配置运行；如果你本机 MySQL 地址不同，请先修改 `.env`

## License

MIT

## 虚拟环境

推荐先为项目创建独立虚拟环境，避免系统 Python 和全局依赖互相污染。

如果本机还没有 `uv`，可先安装：

```bash
pip install uv
```

创建虚拟环境：

```bash
uv venv .venv --python 3.13
```

激活虚拟环境：

```bash
source .venv/bin/activate
```

激活后安装依赖：

```bash
uv pip install -r requirements.txt
```

如果你不确定当前 shell 是否已经正确激活 `.venv`，可以显式指定解释器：

```bash
uv pip install --python .venv/bin/python -r requirements.txt
```

如果你本机同时装了多个 Python，建议先确认当前虚拟环境版本：

```bash
python --version
```

预期输出应类似：

```bash
Python 3.13.x
```

使用虚拟环境中的 Python 启动项目：

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 18003
```

退出虚拟环境：

```bash
deactivate
```

## 运维指南
下载依赖
```bash
uv pip install -r requirements.txt
```
运行项目
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 18003
```

## 常见问题

### 1. 启动时报 `No module named '_sqlite3'`

原因：

- 当前 Python 环境没有编译 `sqlite3` 模块
- 只有当你把 `DATABASE_URL` 改成 SQLite 时才会触发这个问题

处理方式：

1. 优先使用 MySQL，按 `.env.example` 配置 `DATABASE_URL`
2. 如果你确实要切回 SQLite，再使用带 `sqlite3` 模块的 Python 环境

示例：

```bash
cp .env.example .env
```
