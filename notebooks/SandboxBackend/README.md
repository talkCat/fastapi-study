# SandboxBackend 学习计划

这一组 Notebook 用来学习 Clawith 项目的默认沙盒技术（subprocess + bubblewrap）。

源码参考：

- `/home/dev/bxc/Clawith/backend/app/services/sandbox/` — 沙盒模块根目录
- `base.py` — `SandboxBackend` Protocol、`ExecutionResult`、`BaseSandboxBackend`
- `config.py` — `SandboxType` 枚举、`SandboxConfig` 模型
- `registry.py` — `get_sandbox_backend()` 工厂 + 注册表
- `local/subprocess_backend.py` — 默认后端完整实现

学习目标不是把源码抄一遍，而是理解一套生产级沙盒系统的**设计思路**：

```text
安全是设计出来的，不是靠堆砌检查。
—— 纵深防御（Defense in Depth）
```

每一份 Notebook 会先构建一个**简化版**，再对照 Clawith 的真实实现，看清每一层设计的意图。

## 学习顺序

### 001 — Understanding Code Sandboxes

文件：

- `001-understanding-code-sandboxes.ipynb`

目标：

1. 理解为什么需要代码沙盒
2. 亲眼看到直接执行代码的危险（演示 rm -rf、fork bomb 的杀伤力）
3. 理解隔离的四个维度：文件系统、网络、进程、资源
4. 了解 Clawith 沙盒的全景：插件式架构、bwrap 位置、纵深防御
5. 形成"沙盒是一系列约束的组合"的心智模型

### 002 — Architecture of Sandbox Backend

文件：

- `002-architecture-of-sandbox-backend.ipynb`

目标：

1. 理解 Protocol + ABC 的接口设计
2. 用 Python 实现 `ExecutionResult`、`SandboxBackend` Protocol
3. 实现简化版 `SandboxConfig` 和 `SandboxType`
4. 实现注册表模式和工厂函数
5. 对比 Clawith `sandbox/base.py` + `config.py` + `registry.py`

### 003 — Subprocess and Bubblewrap

文件：

- `003-subprocess-and-bubblewrap.ipynb`

目标：

1. 用 asyncio 执行一个子进程并捕获输出
2. 理解 bubblewrap 的基本原理
3. 手动构建 bwrap 命令，理解每个 namespace flag 的作用
4. 用 bwrap 隔离文件系统和进程空间
5. 对比 Clawith `_build_bwrap_command()` 和 `_build_command()`

### 004 — Security Checks and Resource Limits

文件：

- `004-security-and-resource-limits.ipynb`

目标：

1. 理解静态安全检查的边界（能挡住什么、挡不住什么）
2. 实现简化版危险模式检测
3. 用 `setrlimit()` 限制子进程资源
4. 理解环境变量清洁和路径安全
5. 对比 Clawith `_check_code_safety()` 和 `_build_preexec_fn()`

### 005 — Putting It All Together

文件：

- `005-putting-it-all-together.ipynb`

目标：

1. 把前四份 Notebook 的组件拼成完整沙盒系统
2. 用双层配置（env + per-tool）控制沙盒行为
3. 运行对比实验：有 bwrap vs 无 bwrap、有网络 vs 无网络
4. 对照 Clawith `agent_tools.py` 的完整调用链
5. 理解"fail closed"设计、register 扩展性、纵深防御

## 学习原则

1. 先跑通最小例子，再叠隔离层。
2. 不要只调 API，要看每一层隔离在**防御什么**。
3. 每份 Notebook 结尾都要翻源码，对比 Clawith 是怎么做到的。
4. 安全默认值优先，不要为了"方便"放松约束。
