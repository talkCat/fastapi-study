# Jupyter服务启动流程及密码Token记录

## 一、前置操作：激活虚拟环境

启动Jupyter服务前，需先激活项目专属虚拟环境，保证依赖环境正常生效，执行命令如下：

```bash
source /home/dev/bxc/fastapi-study/.venv/bin/activate
```

命令执行成功后，终端前缀会显示 **\(\.venv\)**，代表虚拟环境激活成功，当前处于fastapi\-study项目虚拟环境中。

## 二、Jupyter服务后台启动命令

在激活虚拟环境的终端路径 `~/bxc/fastapi-study` 下，执行后台启动命令，可实现无浏览器启动、监听全网IP、日志持久化输出：

```bash
nohup jupyter-notebook --ip=0.0.0.0 --port=8888 --no-browser > jupyter.log 2>&1 
```

启动返回进程ID：**\[1\] 2558986**，代表Jupyter服务进程已后台运行，所有运行日志将统一输出至当前目录的 `jupyter.log` 文件。

## 三、Token密码查询方式及有效密钥

### 1\. 查询命令

通过过滤日志文件，快速提取Jupyter登录Token，执行命令：

```bash
cat jupyter.log | grep token
```

### 2\. 有效Token密钥

本次服务启动生成的唯一登录Token：

**6cb572d451d509fd963ecc62638b7a470fb2cd2c64bc1656**

## 四、服务访问地址说明

### 1\. 有效远程访问地址（推荐）

**http://gpu\-server:8888/tree?token=6cb572d451d509fd963ecc62638b7a470fb2cd2c64bc1656**

该地址可通过服务器外网/局域网域名远程访问Jupyter服务，适配本地电脑远程连接场景。

### 2\. 本地回环地址（仅服务器本机可用）

http://127\.0\.0\.1:8888/tree?token=6cb572d451d509fd963ecc62638b7a470fb2cd2c64bc1656

该地址仅能在GPU服务器本机访问，外部设备打开会提示 **URL拼写可能存在错误，请检查**，属于正常访问限制，非服务故障。

## 五、核心操作总结

- 启动前提：必须先激活项目虚拟环境，避免依赖缺失报错；

- 运行模式：nohup后台常驻运行，关闭终端不中断服务；

- 访问要点：远程连接务必使用 **gpu\-server域名地址**，禁用127\.0\.0\.1本地地址；

- 日志溯源：所有服务运行日志、报错信息均存储在 `jupyter.log`，故障可通过日志排查。

> （注：文档部分内容可能由 AI 生成）
