<div align="center">

# API Tool

**一个自托管的 API 调试工作站：HTTP 调试 + MCP 客户端 + LLM Playground，三合一。**

不登录、不强制联网、数据不出本机。下载单文件即可用，也能 Docker 一条命令跑在服务器上给团队共用。

<!-- 把下面这行换成你的主界面截图/GIF，README 的点击率全靠它 -->

<!-- ![screenshot](docs/images/main.png) -->

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)
![Arco Design](https://img.shields.io/badge/UI-Arco%20Design-165DFF)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

---

## 这是什么

用过 Postman / Apifox 的人都懂：调一个 AI 相关的接口，往往要在三个工具之间来回切——

- 用 **Postman** 调 HTTP 接口；
- 开另一个客户端连 **MCP Server** 测工具；
- 再开一个 **Chatbox / NextChat** 调大模型流式输出。

**API Tool 把这三件事塞进了同一个工作台**，而且全部跑在你自己的机器或服务器上：请求、MCP 调用、LLM 对话的历史统一管理，集合和环境变量一套通用。

> 适合谁：后端 / AI 应用开发者、想在内网或无外网环境里调试接口和 Agent 工具链的团队、对"API Key 不该上传到第三方云端"有执念的人。

## ✨ 核心亮点

### 1. 三合一工作台，互不切换

| 模块               | 能力                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| **HTTP 调试台**    | 7 种方法、Headers/Query、JSON / Raw / form-data / multipart 文件上传、**响应流式下发（NDJSON，边下边看）**、耗时与体积统计、历史记录 |
| **MCP 客户端**     | 连接 **Streamable HTTP** 类型的 MCP Server，一键测试连通、列出工具、可视化填参调用；支持**临时连接**（填个 URL 就连，不用先存）      |
| **LLM Playground** | 接入任意 **OpenAI 兼容**接口（官方 / DeepSeek / 本地 vLLM / Ollama 网关……），**SSE 流式逐字输出**，Provider 适配器可扩展             |
| **WebSocket**      | wss 连接、收发消息实时日志，调试推送类接口                                                                                           |

### 2. 敏感数据加密落盘，不是明文 JSON

集合里常存着 `Authorization: Bearer xxx`、`X-API-Key` 这种东西。本工具对**敏感字段做字段级加密**：

- **Windows**：直接调用系统 **DPAPI（CryptProtectData）**，密钥绑定"当前用户 + 本机"，拷走密文文件到别的机器/账号也解不开，**零额外依赖**；
- **Linux / macOS**：Fernet (AES-128-CBC)，密钥自动生成到 `~/.api-tool/.master.key`（权限 600），或用环境变量 `API_TOOL_MASTER_KEY` 指定；
- 密文统一带 `enc:v1:` 前缀，**老数据明文自动兼容、平滑迁移**，不用手动导。

### 3. 单文件自托管，不装环境也能跑

后端用 PyInstaller 打成**单文件可执行程序**，内置 Python 运行时和前端页面：

```bash
# Linux 服务器：丢上去就能跑，不需要装 Python / Node
./api-tool --host 0.0.0.0 --port 8765
# 或 Docker
docker compose up -d
```

数据目录、端口、监听地址全部可配，`nohup` 挂后台就是一个团队内网共享的 API 工作台。

### 4. 团队协作版（单实例多用户）

- 本地注册多账号，**创建团队、邀请成员**；
- 每个用户有自己的集合、历史、环境变量，互不串号；
- 适合小团队在内网部署一套，共享 MCP Server / LLM Provider 配置。

### 5. 这些细节做到了 Postman 的手感

- **环境变量插值**：请求里写 `{{baseUrl}}/users`，按当前环境自动替换；支持变量嵌套引用，缺变量发送前提醒；
- **curl 一键导入**：粘贴浏览器里复制出来的 `curl` 命令，自动解析出 method / url / headers / body——shell 分词严格按 POSIX 处理，**Windows 路径 `D:\a.png` 里的反斜杠不会丢**，支持行尾 `\` 续行；
- **请求转代码**：一键生成 `curl` / `Java HttpClient` / `OkHttp` / `Python requests` / `http.client`，Monaco 语法高亮；
- **集合树**：文件夹 / 请求自由组织，保存常用请求。

## 🚀 快速开始

### 方式一：下载可执行文件（推荐）

从 [Releases](../../releases) 下载对应平台的单文件：

```bash
# Linux
chmod +x api-tool
./api-tool                       # 打开 http://localhost:8765

# 自定义端口 / 数据目录 / 对外监听
./api-tool --port 9000 --host 0.0.0.0 --data-dir /srv/api-tool-data
```

Windows 下双击 `api-tool.exe` 即可。

### 方式二：Docker

```bash
docker compose up -d
# 访问 http://localhost:8765
```

### 方式三：源码运行（开发）

```bash
# 后端
cd backend
pip install -e .
$env:APP_ENV="development"          # Linux/macOS: export APP_ENV=development
uvicorn backend.main:app --reload --port 8765

# 前端（另一个终端）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

## 📦 打包

```bash
# Linux 单文件（内置前端 dist，无 GUI headless）
./build-linux.sh
./build-linux.sh --skip-frontend                    # 复用已有前端产物
./build-linux.sh --pip-index https://pypi.tuna.tsinghua.edu.cn/simple

# Windows GUI
cd frontend && npm run build
cd ../backend && pyinstaller launcher.spec
# 产物 backend/dist/api-tool.exe
```

## ⚙️ 配置

数据目录默认 `~/.api-tool/`（Windows 为 `%USERPROFILE%\.api-tool\`），可用 `--data-dir` 或环境变量 `APP_CONFIG_DIR` 覆盖：

| 文件               | 内容                                     |
| ------------------ | ---------------------------------------- |
| `collections.json` | 集合 / 文件夹 / 请求树                   |
| `history.json`     | HTTP / MCP / LLM 调用历史                |
| `config.json`      | MCP Server、LLM Provider、用户与团队配置 |

命令行参数 > 环境变量 > 默认值：

| 命令行       | 环境变量              | 默认值        | 说明                                 |
| ------------ | --------------------- | ------------- | ------------------------------------ |
| `--host`     | `APP_HOST`            | `127.0.0.1`   | 对外服务用 `0.0.0.0`                 |
| `--port`     | `APP_PORT`            | `8765`        | 监听端口                             |
| `--data-dir` | `APP_CONFIG_DIR`      | `~/.api-tool` | 数据目录                             |
| —            | `APP_ENV`             | `production`  | `development` 开启 CORS、走 Vite dev |
| —            | `API_TOOL_MASTER_KEY` | 自动生成      | 非 Windows 平台加密主密钥            |

## 🛠 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Arco Design Vue + Pinia + Vue Router + Monaco Editor
- **后端**：Python 3.10+ / FastAPI / Uvicorn / httpx / Pydantic v2
- **MCP**：官方 Python MCP SDK（Streamable HTTP）
- **加密**：Windows DPAPI（ctypes 直调，无第三方依赖）/ Fernet (cryptography)
- **分发**：PyInstaller 单文件、Docker

## 🗺 路线图

- [x] 环境 / 集合导入导出（Postman Collection v2.1 兼容）
- [x] 请求之间的断言与简单测试脚本
- [x] SSE 原生事件视图（现在走 NDJSON 透传）
- [x] 更多 LLM Provider 适配器（Anthropic 原生格式等）
- [x] 深色模式
