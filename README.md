# API Tool

本地 API 调试工具，集成 HTTP 请求调试（Postman 风格）、MCP（Streamable HTTP）客户端、OpenAI Compatible 大模型调用。

## 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Arco Design Vue + Pinia + Monaco Editor
- **后端**：Python FastAPI + uvicorn + httpx + Pydantic
- **MCP**：Python MCP SDK（Streamable HTTP）
- **大模型**：OpenAI Compatible API 优先，Provider Adapter 扩展
- **打包**：PyInstaller（Linux 单文件 headless 程序 / Windows exe）

## 开发启动

### 后端

```bash
cd backend
pip install -e .
# 开发模式（启用 CORS，前端走 Vite dev server）
export APP_ENV=development   # Windows: $env:APP_ENV="development"
uvicorn backend.main:app --reload --port 8765
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

## Linux 生产打包（无界面单文件）

在 Linux 上把项目打包为单个可执行文件（内置 Python 运行时 + 前端 dist，无需安装 Python/Node，无 GUI）：

```bash
./build-linux.sh                              # 一键打包，产物 backend/dist/api-tool
./build-linux.sh --skip-frontend              # 复用已有 frontend/dist
./build-linux.sh --pip-index https://pypi.tuna.tsinghua.edu.cn/simple   # 使用 pip 镜像
./build-linux.sh --no-clean                   # 保留 PyInstaller 缓存加速二次构建
```

运行（支持自定义端口 / 数据目录 / 监听地址）：

```bash
./api-tool                                    # 本机访问 http://localhost:8765
./api-tool --port 9000 --data-dir /srv/api-tool-data     # 自定义端口与数据目录
./api-tool --host 0.0.0.0 --port 8765         # 服务器对外服务
nohup ./api-tool --port 8765 > api-tool.log 2>&1 &       # 后台运行
```

## Windows 打包（GUI）

```bash
cd frontend && npm run build
cd ../backend && pyinstaller launcher.spec
# 产物位于 dist/api-tool.exe
```

## 配置文件

数据目录默认 `~/.api-tool/`（Linux）或 `%USERPROFILE%\.api-tool\`（Windows），可用 `--data-dir` 或 `APP_CONFIG_DIR` 覆盖：

- `collections.json`：集合 / 文件夹 / 请求树
- `history.json`：HTTP / MCP / LLM 调用历史
- `config.json`：MCP Server、LLM Provider 配置

## 启动参数与环境变量

命令行参数 > 环境变量 > 默认值：

| 命令行 | 环境变量 | 默认值 | 说明 |
|---|---|---|---|
| `--host` | `APP_HOST` | `127.0.0.1` | 监听地址，对外服务用 `0.0.0.0` |
| `--port` | `APP_PORT` | `8765` | 监听端口 |
| `--data-dir` | `APP_CONFIG_DIR` | `~/.api-tool` | 数据目录 |
| — | `APP_ENV` | `production` | `development` 启用 CORS；`production` 托管前端静态资源 |
