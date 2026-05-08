# FastAPI 异步与高并发学习指南

这份指南专门写给有 Java 背景、正在学习 Python 和 FastAPI 的开发者。

## 先建立正确心智模型

在 Java Web 项目里，你更熟悉的是“一个请求占一个工作线程”的模型。  
FastAPI 常见的高吞吐写法不是靠“开更多线程”，而是：

- IO 密集任务：优先用 `async def` + `await`
- 阻塞代码：丢给线程池
- CPU 密集任务：交给进程池或独立 worker

可以先把它理解为：

- Java `CompletableFuture + 非阻塞 IO` ≈ Python `asyncio`
- Java `@Async / ThreadPoolTaskExecutor` ≈ Python `run_in_threadpool()` / `asyncio.to_thread()`
- Java MQ / Job worker ≈ Python `Celery / RQ / 独立进程`

## 场景 1：异步线程到底怎么理解

Python 里经常把“异步”和“线程”混在一起说，但它们不是一回事：

- `async def` 不是新线程，它运行在事件循环里
- `await` 的意义是：遇到 IO 等待时让出执行权
- 线程池是用来接住阻塞函数的，不是所有代码都该丢线程池

### 什么时候该写 `async def`

适合：

- 查数据库
- 调外部 HTTP API
- 访问 Redis
- 读写消息队列

前提是你使用的客户端本身支持异步。  
如果底层库本来就是阻塞的，你把函数签名改成 `async def` 也没有意义。

### 什么时候该用线程池

适合：

- 阻塞文件操作
- 老旧同步 SDK
- 同步数据库驱动
- 短时间阻塞型计算或格式转换

在本项目中对应示例接口：

- `GET /api/v1/learning/async-io-demo`
- `GET /api/v1/learning/threadpool-demo`
- `POST /api/v1/learning/background-task-demo`

## 场景 2：高并发到底要优化什么

很多 Java 开发者刚接触 FastAPI 时，会下意识关注“线程数”。  
但在 Python Web 服务里，更关键的是下面这些点：

- 不阻塞事件循环
- 控制对下游资源的并发冲击
- 让单请求资源消耗可预测

### 高并发下最容易踩的坑

1. 在 `async def` 里写阻塞代码
2. 一个请求里无上限并发下游调用
3. 单接口返回全量数据
4. 慢 SQL、无索引、无分页
5. 对第三方 API 不设超时

### 推荐做法

1. IO 密集优先异步化
2. 阻塞代码下沉线程池
3. 使用 `asyncio.Semaphore` 控制 fan-out 并发
4. 给数据库连接池、HTTP 客户端、Redis 客户端配置超时
5. 接口设计默认分页、过滤、批量化

在本项目中对应示例接口：

- `POST /api/v1/learning/bounded-concurrency-demo`

它会模拟多个子任务并发执行，并通过 `max_concurrency` 演示“受控并发”和“无脑全开”的区别。

## 场景 3：CPU 密集任务怎么处理

这类任务包括：

- 图片压缩
- Excel 大报表导出
- 大量 JSON 序列化/反序列化
- 模型推理

这时：

- `async def` 帮不了你
- 线程池收益通常有限
- 更适合进程池或独立 worker

实践上，Web 接口应快速返回：

- `task_id`
- `status=queued`

再由后台 worker 异步处理，客户端轮询结果或通过回调获取结果。

在本项目中对应示例接口：

- `POST /api/v1/learning/cpu-task-demo`
- `GET /api/v1/learning/cpu-task-demo/{task_id}`

这里用 `ProcessPoolExecutor` 做了一个最小可运行示例：

- 提交时立即返回 `task_id`
- CPU 计算在独立进程中执行
- 客户端通过查询接口轮询 `queued/running/completed/failed`

## 学习顺序建议

1. 先请求 `GET /api/v1/learning/best-practices` 看概念归类
2. 再请求 `GET /api/v1/learning/async-io-demo`
3. 对比 `GET /api/v1/learning/threadpool-demo`
4. 调用 `POST /api/v1/learning/bounded-concurrency-demo`
5. 最后体验 `POST /api/v1/learning/cpu-task-demo` 和查询接口

## 你可以重点对照 Java 的几个类比

1. FastAPI 的高并发核心不是“疯狂开线程”，而是“尽量非阻塞”
2. Python 线程池更像 Java 的兜底方案，用来接住阻塞代码
3. 复杂耗时任务不要塞进请求链路，应拆到后台 worker

## 对应接口测试

项目里已经补了学习模块的接口测试：

- `tests/test_learning_endpoints.py`

运行方式：

```bash
python -m unittest tests.test_learning_endpoints
```
