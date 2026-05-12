# Python 语法录

这份笔记专门记录本项目中比较容易让 Java 开发者困惑的 Python 语法。

## 1. 列表推导式

示例代码：

```python
batches = [chunks[index:index + batch_size] for index in range(0, len(chunks), batch_size)]
```

它等价于下面这种更展开的写法：

```python
batches = []
for index in range(0, len(chunks), batch_size):
    batches.append(chunks[index:index + batch_size])
```

可以理解为：

- `for index in range(...)`：遍历索引
- `chunks[index:index + batch_size]`：每次从原列表里切出一段
- 外层 `[...]`：把每次切出来的结果收集成一个新列表

在这个例子里，它的作用是把 `chunks` 按 `batch_size` 分批。

例如：

```python
chunks = [1, 2, 3, 4, 5]
batch_size = 2
```

结果会是：

```python
[[1, 2], [3, 4], [5]]
```

## 2. 列表切片

示例：

```python
chunks[index:index + batch_size]
```

这是 Python 的切片语法，含义是：

- 从 `index` 开始
- 一直到 `index + batch_size`
- 右边界不包含

例如：

```python
numbers = [10, 20, 30, 40, 50]
numbers[1:3]
```

结果：

```python
[20, 30]
```

这和 Java 的 `subList(start, end)` 很像，但语法更短。

## 3. `range(start, stop, step)`

示例：

```python
range(0, len(chunks), batch_size)
```

含义：

- 从 `0` 开始
- 到 `len(chunks)` 结束
- 每次步长是 `batch_size`

例如：

```python
list(range(0, 10, 3))
```

结果：

```python
[0, 3, 6, 9]
```

## 4. 类型注解

示例：

```python
chunks: list[dict]
```

意思是：

- `chunks` 是一个列表
- 列表里的每一项都是 `dict`

以及：

```python
) -> int:
```

表示这个函数返回 `int`。

这只是“类型提示”，方便阅读、IDE 补全和静态检查，并不是 Java 那种强制编译期类型系统。

## 5. 内层函数

示例：

```python
async def write_one_batch(batch: list[dict]) -> int:
```

这是在一个函数内部再定义一个函数。

可以理解为：

- 这个函数只在当前方法里使用
- 不想暴露成类方法或模块级函数

Java 里比较像：

- 局部 lambda
- 局部内部类

## 6. `async def`

示例：

```python
async def _simulate_external_index_write(...):
```

表示这是一个异步函数。

特点：

- 调用它时不会立刻执行到底
- 需要 `await` 才真正等待结果

例如：

```python
result = await some_async_func()
```

## 7. `async with`

示例：

```python
async with semaphore:
```

它和普通的：

```python
with lock:
```

很像，只不过这里进入和退出上下文时允许异步等待。

在这个项目里，`semaphore` 是 `asyncio.Semaphore`，作用是：

- 限制同一时间最多有多少个协程进入这一段代码

所以这句的含义是：

- 先尝试获取一个并发名额
- 用完后自动释放

## 8. `await`

示例：

```python
await asyncio.sleep(per_batch_delay_ms / 1000)
```

`await` 的意思不是“开线程”，而是：

- 当前协程先暂停
- 把执行权交还给事件循环
- 等这个异步操作完成后再继续

这和 Java 里阻塞等待不是一个概念，更像“挂起当前任务”。

## 9. 生成器表达式

示例：

```python
(write_one_batch(batch) for batch in batches)
```

它和列表推导式长得很像，但外面是 `()`，不是 `[]`。

区别：

- 列表推导式：立刻生成完整列表
- 生成器表达式：按需产生结果

这里的作用是把一批协程对象逐个交给 `asyncio.gather(...)`。

## 10. `*` 解包

示例：

```python
await asyncio.gather(*(write_one_batch(batch) for batch in batches))
```

这里的 `*` 表示“解包”。

假设你有：

```python
tasks = [task1, task2, task3]
```

那么：

```python
func(*tasks)
```

等价于：

```python
func(task1, task2, task3)
```

所以这里的意思是：

- 先生成很多个 `write_one_batch(...)` 协程
- 再把它们一个个传给 `asyncio.gather(...)`

## 11. `asyncio.gather(...)`

示例：

```python
results = await asyncio.gather(*(write_one_batch(batch) for batch in batches))
```

作用：

- 并发执行多个协程
- 等它们都完成
- 按顺序收集返回结果

例如：

```python
results = await asyncio.gather(task_a(), task_b(), task_c())
```

结果可能是：

```python
[result_a, result_b, result_c]
```

## 12. `sum(results)`

示例：

```python
return sum(results)
```

如果 `results` 是一组数字，比如：

```python
[2, 2, 1]
```

那么：

```python
sum(results)
```

结果就是：

```python
5
```

在这个项目里，它表示“所有批次总共写入了多少文档”。

## 对应到本项目这段代码

原始代码：

```python
batches = [chunks[index:index + batch_size] for index in range(0, len(chunks), batch_size)]

async def write_one_batch(batch: list[dict]) -> int:
    async with semaphore:
        await asyncio.sleep(per_batch_delay_ms / 1000)
        return len(batch)

results = await asyncio.gather(*(write_one_batch(batch) for batch in batches))
return sum(results)
```

按“人话”翻译就是：

1. 先把所有文本块按 `batch_size` 分批
2. 每一批都定义成一个异步写入任务
3. 用 `Semaphore` 控制同时最多跑多少批
4. 用 `asyncio.gather` 并发执行这些批任务
5. 最后把每批写入数量加总返回
