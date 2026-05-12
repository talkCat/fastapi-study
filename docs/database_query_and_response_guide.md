# FastAPI 查库流程与统一返回体学习指南

这份文档专门写给有 Java 背景、正在学习 Python 和 FastAPI 的开发者。

目标只有两个：

1. 看懂一个请求是怎么一路查到数据库的
2. 看懂项目里的统一 RESTful 返回体是怎么落地的

可以把它理解成：

- Java `Controller -> Service -> Mapper/DAO -> DB`
- FastAPI `router -> service -> repository -> SQLAlchemy -> DB`

---

## 1. 先看整体链路

以教学接口 `GET /api/v1/demo-records/` 为例，请求链路如下：

```text
HTTP 请求
  -> router: app/api/routers/demo_records.py
  -> service: app/services/demo_record.py
  -> repository: app/db/repository.py
  -> model: app/models/demo_record.py
  -> MySQL
  -> schema: app/schemas/demo_record.py
  -> ApiResponse/PageData
  -> JSON 响应
```

如果你熟悉 Java，可以这样对照：

| FastAPI | Java 常见角色 |
|------|------|
| `router` | `Controller` |
| `Depends(get_db)` | Spring 注入 `Session` / `EntityManager` |
| `service` | `Service` |
| `repository` | `DAO` / `Mapper` |
| `model` | `Entity` / `PO` |
| `schema` | `DTO` / `VO` |
| `ApiResponse<T>` | `Result<T>` |

---

## 2. 请求是怎么拿到数据库连接的

数据库入口在：

- `app/db/database.py`

核心逻辑可以拆成 3 步。

### 第 1 步：创建 engine

```python
_engine = create_engine(
    settings.database_url,
    connect_args=_get_connect_args(),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

它的作用类似 Java 里的 `DataSource`。

- `settings.database_url`：数据库连接串
- `echo=settings.debug`：开启后会把 ORM 生成的 SQL 打印出来
- `pool_pre_ping=True`：取连接前先探活，避免连接失效
- `pool_recycle=3600`：连接定期回收

### 第 2 步：创建 session factory

```python
_session_factory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=get_engine()
)
```

这一步可以类比 Java 里的：

- `SqlSessionFactory`
- `EntityManagerFactory`

### 第 3 步：每个请求分配一个 Session

```python
def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
```

这就是 FastAPI 的依赖注入写法。

谁在 router 里声明：

```python
db: Session = Depends(get_db)
```

谁就能在当前请求中拿到数据库会话。

可以把它理解成：

- 请求开始：创建一个 `Session`
- 请求结束：自动 `close()`

---

## 3. router 层做什么

看 `app/api/routers/demo_records.py` 里的列表接口：

```python
@router.get("/", response_model=ApiResponse[PageData[DemoRecord]])
def list_demo_records(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    records = demo_record_service.list_records(db, skip=skip, limit=limit)
    total = demo_record_repository.count(db)
    return page_response(records, total=total, skip=skip, limit=limit, message="查询成功")
```

router 只做这些事：

1. 接收请求参数
2. 注入 `db`
3. 调用 service / repository
4. 把结果包装成统一返回体

这和 Java Controller 的职责很像：

- 不写复杂业务
- 不直接拼 SQL
- 负责请求和响应的边界

---

## 4. service 层做什么

看：

- `app/services/demo_record.py`

```python
def list_records(self, db: Session, skip: int = 0, limit: int = 20):
    return self.repository.get_all(db, skip=skip, limit=limit)
```

这个 demo 里的 service 很薄，主要是教学用途。

真实项目里，service 常常负责：

1. 业务规则编排
2. 调多个 repository
3. 控制事务边界
4. 做权限、状态、幂等、补偿等业务判断

所以可以这样理解：

- router：接 HTTP
- service：处理业务
- repository：只做数据访问

---

## 5. repository 层为什么没写 SQL

看：

- `app/db/repository.py`

```python
def get_all(self, db: Session, skip: int = 0, limit: int = 100):
    return db.query(self.model).offset(skip).limit(limit).all()
```

以及：

```python
def get(self, db: Session, id: int):
    return db.query(self.model).filter(self.model.id == id).first()
```

你没看到 SQL，是因为这里用的是 ORM，不是手写 SQL。

SQLAlchemy 会根据这些 ORM 表达式自动生成 SQL。

例如这句：

```python
db.query(self.model).filter(self.model.id == id).first()
```

背后大致会变成：

```sql
select * from demo_records where id = ? limit 1
```

再比如：

```python
db.query(self.model).offset(skip).limit(limit).all()
```

背后大致会变成：

```sql
select * from demo_records limit ? offset ?
```

### 想看真实 SQL 怎么办

把 `.env` 里的：

```env
DEBUG=true
```

打开后，`create_engine(..., echo=settings.debug)` 会打印 SQL。

这点很像 Java 里打开 MyBatis SQL 日志。

---

## 6. 表和字段是怎么映射的

看：

- `app/models/demo_record.py`

```python
class DemoRecordModel(Base):
    __tablename__ = "demo_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    owner = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

它可以类比成：

- `@Table(name = "demo_records")`
- `@Column(name = "title")`

也就是说：

- 类 `DemoRecordModel` 对应表 `demo_records`
- 属性 `title` 对应列 `title`
- 属性 `owner` 对应列 `owner`

这就是 ORM 的字段映射。

---

## 7. 创建、更新、删除是怎么提交的

还是看：

- `app/db/repository.py`

### 新增

```python
def create(self, db: Session, obj_in: dict):
    db_obj = self.model(**obj_in)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
```

可以这样理解：

1. `self.model(**obj_in)`：把请求数据变成 ORM 对象
2. `db.add(...)`：放进当前 Session
3. `db.commit()`：提交事务
4. `db.refresh(...)`：把数据库生成的最新值查回来

`refresh()` 常见用途：

- 回填主键 `id`
- 回填数据库默认值

### 更新

```python
for key, value in obj_in.items():
    setattr(db_obj, key, value)
db.commit()
db.refresh(db_obj)
```

这相当于：

- 先查出对象
- 再逐个属性赋值
- 然后提交事务

### 删除

```python
db.delete(db_obj)
db.commit()
```

这就是真正执行删除。

---

## 8. 分页是怎么实现的

目前项目里的基础分页是：

```python
offset(skip).limit(limit)
```

含义是：

- `skip`：跳过多少条
- `limit`：取多少条

这就是常见的偏移分页。

例如：

- `skip=0, limit=20`：查第一页前 20 条
- `skip=20, limit=20`：查第二页 20 条

### 为什么还要额外查 `total`

因为前端通常不只要当前页数据，还要知道总记录数。

所以现在列表接口会做两次查询：

1. 查当前页数据
2. 查总数 `count(*)`

例如：

```python
records = demo_record_service.list_records(db, skip=skip, limit=limit)
total = demo_record_repository.count(db)
return page_response(records, total=total, skip=skip, limit=limit, message="查询成功")
```

### 返回给前端的分页结构

现在统一成：

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "demo"
      }
    ],
    "total": 36,
    "skip": 0,
    "limit": 20
  }
}
```

这和 Java 项目里常见的：

- `PageResult<T>`
- `PageInfo<T>`
- `CommonPage<T>`

是一个思路。

---

## 9. schema 层做什么

看：

- `app/schemas/demo_record.py`

这里有几类模型：

### 请求模型

```python
class DemoRecordCreate(DemoRecordBase):
    pass
```

它负责校验请求参数。

例如：

- `title` 必填
- 长度限制
- `owner` 必填

### 响应模型

```python
class DemoRecordInDB(DemoRecordBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
```

这里的：

```python
from_attributes=True
```

意思是：

- 即使返回的是 ORM 对象
- Pydantic 也会按对象属性去读取并转成 JSON

这可以类比成：

- Java 中把 Entity 转成 ResponseDTO

只不过这里很多时候是框架自动完成的。

---

## 10. 统一返回体是怎么设计的

核心文件：

- `app/schemas/common.py`
- `app/core/responses.py`

### 通用成功结构

```python
class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    data: T | None = None
```

这就是通用返回体。

可以类比 Java：

```java
class Result<T> {
    private Integer code;
    private String message;
    private T data;
}
```

### 分页结构

```python
class PageData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
```

可以类比 Java：

```java
class PageResult<T> {
    private List<T> items;
    private Long total;
    private Integer skip;
    private Integer limit;
}
```

### 统一包装函数

```python
def success_response(data=None, message: str = "success", code: int = 200):
    return ApiResponse(code=code, message=message, data=data)
```

以及：

```python
def page_response(items, total, skip, limit, message: str = "success", code: int = 200):
    return ApiResponse(
        code=code,
        message=message,
        data=PageData(items=items, total=total, skip=skip, limit=limit),
    )
```

这就很像 Java 里常见的：

- `Result.success(data)`
- `PageResult.success(list, total)`

---

## 11. 错误为什么也要统一格式

项目在：

- `app/main.py`

里加了全局异常处理。

### HTTP 异常

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(...):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": message,
            "data": None,
        },
    )
```

这样 `404`、`403`、`400` 这类异常也会统一成：

```json
{
  "code": 404,
  "message": "教学记录不存在",
  "data": null
}
```

### 参数校验异常

```python
@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(...):
```

会统一成：

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

这和很多 Java 项目里自定义全局异常处理器是同一种思路。

---

## 12. 一次完整查库流程复盘

还是以：

- `GET /api/v1/demo-records/?skip=0&limit=20`

为例。

### 第 1 步：请求进入 router

router 收到参数：

- `skip=0`
- `limit=20`
- `db=Depends(get_db)` 注入数据库会话

### 第 2 步：调用 service

```python
records = demo_record_service.list_records(db, skip=skip, limit=limit)
```

### 第 3 步：service 调 repository

```python
return self.repository.get_all(db, skip=skip, limit=limit)
```

### 第 4 步：repository 生成 ORM 查询

```python
db.query(self.model).offset(skip).limit(limit).all()
```

### 第 5 步：SQLAlchemy 执行真实 SQL

大致会生成：

```sql
select * from demo_records limit 20 offset 0
```

### 第 6 步：结果变成 ORM 对象列表

例如：

```python
[
    DemoRecordModel(...),
    DemoRecordModel(...),
]
```

### 第 7 步：router 包装统一返回体

```python
return page_response(records, total=total, skip=skip, limit=limit, message="查询成功")
```

### 第 8 步：Pydantic 序列化成 JSON

最终返回：

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "items": [...],
    "total": 36,
    "skip": 0,
    "limit": 20
  }
}
```

---

## 13. 你现在最应该记住的几点

1. router 不直接写 SQL，它只是接请求、调 service、包响应
2. repository 通过 SQLAlchemy ORM 访问数据库，所以你看不到手写 SQL
3. model 决定表和字段映射关系
4. schema 决定请求校验和响应序列化
5. `ApiResponse<T>` 就是 Python 版 `Result<T>`
6. `PageData<T>` 就是 Python 版分页结果对象
7. 全局异常处理的意义，是让失败响应也保持统一结构

---

## 14. 推荐学习顺序

1. 先读 `app/db/database.py`，理解 `engine -> sessionmaker -> get_db`
2. 再读 `app/models/demo_record.py`，理解表和字段映射
3. 再读 `app/db/repository.py`，理解 ORM 查询和增删改
4. 再读 `app/services/demo_record.py`，理解 service 的职责
5. 再读 `app/api/routers/demo_records.py`，理解请求和响应边界
6. 最后读 `app/schemas/common.py` 和 `app/core/responses.py`，理解统一返回体

---

## 15. 对应测试

你可以通过测试反向观察这套流程和返回结构：

- `tests/test_demo_record_flow.py`
- `tests/test_learning_endpoints.py`

运行方式：

```bash
python -m unittest tests.test_demo_record_flow
python -m unittest tests.test_learning_endpoints
```
