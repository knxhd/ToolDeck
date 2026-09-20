## 为什么

开发者需要一个轻量级的本地 API 调试工具，既能完成 Postman 的 HTTP 请求调试，又能直接调用 MCP（Model Context Protocol）服务器和大模型 API，让 AI 工具链的联调在一个界面内完成，避免在多个工具之间反复切换。现在做是因为 MCP Streamable HTTP 协议已稳定，大模型 API 调用已成为后端开发日常，缺少统一调试入口。

## 变更内容

从零构建一个本地桌面式 Web 应用：双击可执行文件即启动后端服务并自动打开浏览器，前端提供三合一调试工作台。

- 新增 **HTTP 请求工作台**：方法/URL/Header/Body/Params 编辑、请求历史、响应查看，覆盖 Postman 基础能力
- 新增 **MCP 客户端**：仅支持 Streamable HTTP 传输方式，可连接 MCP Server、列出工具、调用工具、查看结果
- 新增 **大模型调用**：优先支持 OpenAI Compatible API（`/v1/chat/completions`），通过 Provider Adapter 扩展其他厂商；支持 SSE 流式响应解析
- 新增 **应用外壳**：Python + FastAPI 后端，`webbrowser + uvicorn` 自动启动浏览器，PyInstaller 打包为单文件可执行程序
- 新增 **前端工程**：Vue 3 + Vite + TypeScript + Element Plus + Pinia + Monaco Editor

## 功能 (Capabilities)

### 新增功能

- `http-request-workbench`: HTTP 请求编辑、发送、历史保存与响应展示，提供 Postman 风格的工作台
- `mcp-streamable-client`: 通过 Streamable HTTP 协议连接 MCP Server，完成 initialize/list tools/call tool 流程与结果展示
- `llm-provider-adapter`: 以 OpenAI Compatible API 为基准的大模型调用，支持流式 SSE 响应解析，通过 Provider Adapter 扩展多厂商
- `app-shell-packaging`: 应用入口、后端服务编排、自动打开浏览器、静态资源托管与 PyInstaller 打包

### 修改功能

<!-- 项目从零开始，无已有规范 -->

## 影响

- **代码**：新建 `backend/`（FastAPI 应用、路由、Pydantic schema、MCP 客户端、LLM adapter）与 `frontend/`（Vue 3 应用）两个顶层目录
- **依赖（后端）**：`fastapi`、`uvicorn`、`pydantic`、`httpx`、`mcp`（Python MCP SDK）、`pyinstaller`
- **依赖（前端）**：`vue@3`、`vite`、`typescript`、`element-plus`、`pinia`、`monaco-editor`
- **运行时**：本地启动一个端口（默认 `127.0.0.1:8765`），仅监听本机，避免外部访问
- **交付物**：`dist/api-tool.exe` 单文件可执行程序，双击运行后自动打开浏览器访问应用
- **API**：后端向前端暴露 RESTful 接口（HTTP 调试、MCP 调用、LLM 调用）+ SSE 流式端点
