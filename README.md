# API Tool

本地 API 调试工具，集成 HTTP 请求调试（Postman 风格）、MCP（Streamable HTTP）客户端、OpenAI Compatible 大模型调用。

## 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Element Plus + Pinia + Monaco Editor
- **后端**：Python FastAPI + uvicorn + httpx + Pydantic
- **MCP**：Python MCP SDK（Streamable HTTP）
- **大模型**：OpenAI Compatible API 优先，Provider Adapter 扩展
- **打包**：PyInstaller（单文件 exe）

## 开发启动

### 后端

```bash
cd backend
pip install -e .
# 开发模式（启用 CORS，前端走 Vite dev server）
$env:APP_ENV="development"
uvicorn backend.main:app --reload --port 8765
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

## 生产打包

```bash
# 1. 构建前端
cd frontend
npm run build

# 2. 打包后端为单文件 exe
cd ../backend
pyinstaller launcher.spec
# 产物位于 dist/api-tool.exe
```

双击 `api-tool.exe` 即可启动并自动打开浏览器。

## 配置文件

- `~/.api-tool/config.json`：MCP Server、LLM Provider 配置
- `~/.api-tool/history.json`：HTTP / MCP / LLM 调用历史

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `production` | `development` 启用 CORS；`production` 托管前端静态资源 |
| `APP_PORT` | `8765` | 启动端口（被占用自动递增到 8775） |
| `APP_HOST` | `127.0.0.1` | 监听地址，固定为本机 |

仅监听 `127.0.0.1`，禁止外部访问。
