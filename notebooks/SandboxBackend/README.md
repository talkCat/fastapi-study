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

## 关键心得到

以下是从学习过程中提炼的核心认知，帮助你在更深层次理解 bwrap 和 Docker 的关系：

### 1. bwrap 和 Docker 用同一套内核 namespace

```text
bwrap:  --unshare-user --unshare-pid --unshare-net ...
Docker: clone(CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET ...)
         ↑ 内核 API 是一样的
```

Docker 不是虚拟机——它和 bwrap 共享同一套 Linux namespace 机制。你感受到的"完全隔离"来自 Docker 的镜像层（overlayfs）和预设配置，不是来自更强的内核原语。

### 2. "一堆定制代码"不是 bwrap 的问题，是配置存放位置不同

| 做的事 | Docker | bwrap |
|---|---|---|
| 只读系统路径 | `FROM xxx` 镜像自带 | `--ro-bind /usr /usr` |
| 可写工作区 | `-v $PWD:/workspace` | `--bind /workspace /workspace` |
| 限制网络 | `--network none` | `--unshare-net` |
| 建立 /tmp /proc /dev | 容器运行时自动 | `--dir /tmp --proc /proc --dev /dev` |

Docker 只是把配置打包进了镜像和 CLI 参数里。bwrap 需要显式写出每一行，但**两者隔离效果等价**。

### 3. bwrap + setrlimit 在某些方面比 Docker 更精细

| 能力 | Docker | bwrap + setrlimit |
|---|---|---|
| 内存限制 | cgroup 容器级 | `RLIMIT_AS` 单进程级 |
| 子进程数 | 不限制（默认） | `RLIMIT_NPROC=32` 防 fork bomb |
| 文件写入量 | 不限制（默认） | `RLIMIT_FSIZE=10MB` |
| core dump | 不限制（默认） | `RLIMIT_CORE=0` 防泄密 |

Docker 容器内一个进程 fork 上千次不会触发任何限制。

### 4. Clawith 的两层 Docker + bwrap = 各司其职

```
Docker 层（部署）: 保证系统自己的 Python 版本、依赖、可复现
bwrap  层（沙盒）: 保证 Agent 每段代码不影响系统内部
```

不是"选一个"，而是两层互补：

- Docker 解决了**部署环境、宿主机不被项目污染**
- bwrap 解决了**每一次代码调用的隔离、不启动容器、低延迟**
- 二者不需要二选一——Clawith 同时用

### 5. bwrap 唯一真正的短板：不能换 runtime 版本

| 场景 | Docker | bwrap |
|---|---|---|
| 需要 Python 3.11，宿主机只有 3.8 | ✅ `FROM python:3.11-slim` | ❌ 只能用宿主机的 |
| 需要 JDK 17，宿主机只有 JDK 11 | ✅ `FROM eclipse-temurin:17` | ❌ 只能用宿主机的 |
| 需要 pandas 3.0 | ✅ 镜像里预装好 | ❌ 除非宿主机也装了 |

如果 Agent 需要特定版本 runtime，Docker 后端或 E2B 云端沙盒是正确选择。

### 6. 纵深防御，不是单一防线

Clawith 沙盒的防线不是 bwrap 一层：

```
① 静态代码扫描    → 拦截明显恶意命令
② 路径安全验证    → 防止目录逃逸
③ bwrap namespace → 文件系统/网络/进程隔离
④ setrlimit      → CPU/内存/进程数/CD 限额
⑤ chroot         → 进一步锁文件系统（root 模式）
⑥ fail closed    → bwrap 不可用时拒绝执行
```

Docker 默认只有第③层部分实现（namespace + cgroup），缺乏①、②、④、⑥。

### 7. Docker socket 是真实攻击面

Docker 沙盒必须挂载 `/var/run/docker.sock`。这意味着沙盒服务进程拥有宿主机 Docker daemon 的完全控制权——可以启动任意容器、挂载任意路径。这是比 bwrap namespace 逃逸大得多的风险面。

bwrap 不需要 socket，完全不需要额外守护进程。

### 8. 内核级限制是共享的

bwrap 和 Docker 都共享宿主机内核，所以对以下攻击都**无法防御**：

```
读取 /proc/cpuinfo 了解 CPU 型号       → 两者都挡不住
Spectre 类侧信道攻击                    → 两者都挡不住
利用内核漏洞提权                       → 两者都挡不住
```

如果需要真正的完全隔离，需要虚拟机（KVM / Firecracker / gVisor）级别的方案。
