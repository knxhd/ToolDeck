## 1. 项目脚手架

- [x] 1.1 在仓库根目录创建 `backend/` 与 `frontend/` 两个顶层目录，根目录添加 `README.md` 描述启动方式
- [x] 1.2 初始化 `frontend/`：`npm create vite@latest frontend -- --template vue-ts`，安装 `vue@3 element-plus pinia monaco-editor vue-router@4`
- [x] 1.3 初始化 `backend/`：创建 `backend/pyproject.toml`，声明依赖 `fastapi uvicorn[standard] pydantic httpx mcp pyinstaller`
- [x] 1.4 在 `backend/.env.example` 中列出 `APP_ENV`、`APP_PORT`、`APP_HOST` 环境变量
- [x] 1.5 配置 `frontend/vite.config.ts`：dev server 5173、`/api` 与 `/sse` 代理到 `http://127.0.0.1:8765`、manual chunk 拆分 Monaco

## 2. 应用外壳与启动流程

- [x] 2.1 创建 `backend/main.py` 入口：解析 `APP_ENV`，调用 `app.create_app()` 得到 FastAPI 实例，启动 uvicorn
- [x] 2.2 实现 `backend/app/port.py`：`find_available_port(start=8765, end=8775)` 函数，通过 `socket.bind` 探测可用端口
- [x] 2.3 实现 `backend/app/launcher.py`：在 uvicorn 启动后异步任务调用 `webbrowser.open_new_tab(f"http://127.0.0.1:{port}")`，等待 2 秒后触发
- [x] 2.4 实现 `backend/app/config.py`：首次启动检测 `~/.api-tool/`，不存在则创建目录并写入默认 `config.json` 与 `history.json`
- [x] 2.5 实现 `backend/app/static.py`：生产模式下挂载 `StaticFiles(directory="frontend/dist")` 到根路径，对非 `/api`、`/sse` 路径返回 `index.html`（SPA fallback）
- [x] 2.6 在 `backend/app/__init__.py` 的 `create_app()` 中根据 `APP_ENV` 决定是否启用 `CORSMiddleware`（仅 development 模式允许 `http://localhost:5173`）
- [x] 2.7 验证：`APP_ENV=development uvicorn backend.main:app --reload` 启动后访问 `http://127.0.0.1:8765/api/health` 返回 200
- [x] 2.8 验证：占用 8765 端口后再次启动，确认自动切换到 8766

## 3. HTTP 请求工作台

### 后端

- [x] 3.1 定义 Pydantic 模型 `backend/app/schemas/http.py`：`HttpRequest`（method, url, headers, params, body_type, body）、`HttpResponse`（status_code, headers, body, elapsed_ms, size_bytes）
- [x] 3.2 实现 `backend/app/services/http_client.py`：用 httpx.AsyncClient 转发请求，支持 JSON/raw/form-data body，30 秒超时，返回完整响应（含耗时与字节数）
- [x] 3.3 实现 `backend/app/api/http.py` 路由：`POST /api/http/send` 接收 `HttpRequest` 返回 `HttpResponse`；`GET /api/http/history` 返回历史列表；`DELETE /api/http/history` 清空
- [x] 3.4 实现 `backend/app/services/history_store.py`：读写 `~/.api-tool/history.json` 的 `http_calls` 数组，最多保留 200 条，按时间倒序淘汰
- [x] 3.5 在 `/api/http/send` 成功后追加一条历史（方法、URL、Headers、Body、状态码、耗时、时间戳）

### 前端

- [x] 3.6 创建 `frontend/src/stores/http.ts` Pinia store：当前请求 state、响应 state、历史列表 state，actions 调用 `/api/http/*`
- [x] 3.7 创建 `frontend/src/views/HttpWorkbench.vue`：三栏布局（左：历史；中：请求编辑；右：响应）
- [x] 3.8 实现请求编辑面板：方法下拉（GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS）、URL 输入、Tabs 切换 Headers/Params/Body
- [x] 3.9 Body 编辑器集成 Monaco Editor，根据 body_type 切换 language（json / plaintext）
- [x] 3.10 实现响应面板：状态码 + 耗时 + 字节数展示，响应头表格（带搜索过滤），响应体 Monaco Editor（JSON 高亮，>5MB 截断提示）
- [x] 3.11 实现历史列表：点击条目加载到编辑面板，「清空历史」按钮二次确认后调用 `DELETE /api/http/history`
- [x] 3.12 验证：发送 `GET https://api.github.com/users/octocat` 成功返回并展示；发送 JSON Body POST 请求被正确转发

## 4. MCP Streamable 客户端

### 后端

- [x] 4.1 定义 Pydantic 模型 `backend/app/schemas/mcp.py`：`McpServer`（name, url, headers）、`McpTool`（name, description, input_schema）、`McpCallResult`
- [x] 4.2 实现 `backend/app/services/mcp_client.py`：封装 `mcp.streamable_http_client`，提供 `initialize(server) -> info`、`list_tools(server) -> list[McpTool]`、`call_tool(server, tool_name, args) -> result` 三个方法
- [x] 4.3 实现 `backend/app/api/mcp.py` 路由：`GET /api/mcp/servers`、`POST /api/mcp/servers`、`PUT /api/mcp/servers/{name}`、`DELETE /api/mcp/servers/{name}`、`POST /api/mcp/servers/{name}/test`（initialize 探测）
- [x] 4.4 实现 `GET /api/mcp/servers/{name}/tools` 返回工具列表，`POST /api/mcp/servers/{name}/tools/{tool}/call` 调用工具
- [x] 4.5 在 config.json 的 `mcp_servers` 字段读写 Server 配置；调用工具后追加历史到 `history.json` 的 `mcp_calls` 数组（最多 100 条）
- [x] 4.6 验证：配置一个本地 MCP Server（或用 https://example.com/mcp 模拟），`POST /test` 端点返回连通性结果

### 前端

- [x] 4.7 创建 `frontend/src/stores/mcp.ts`：servers 列表、当前选中 server 的 tools 列表、最近调用结果
- [x] 4.8 创建 `frontend/src/views/McpClient.vue`：左侧 Server 列表（含添加/编辑/删除/测试按钮），右侧选中 Server 的工具列表
- [x] 4.9 工具卡片展示 name、description、inputSchema 折叠区（Monaco JSON 模式只读）
- [x] 4.10 点击工具打开调用对话框：基于 inputSchema 生成表单（生成失败回退到 Monaco JSON 编辑器），填写后调用 `tools/call`
- [x] 4.11 结果展示面板：text 直接展示，resource/image 展示类型与摘要 + 复制原始内容按钮
- [x] 4.12 「MCP 历史」标签页：展示 `mcp_calls` 历史，点击查看完整参数与结果
- [x] 4.13 验证：添加真实 MCP Server（如本地启动一个 echo server），完成 initialize → list → call 全流程

## 5. LLM Provider Adapter

### 后端

- [x] 5.1 定义 Pydantic 模型 `backend/app/schemas/llm.py`：`LlmProvider`（name, base_url, api_key, model, provider_type, options）、`ChatMessage`（role, content）、`ChatRequest`（provider_name, messages, stream, temperature）
- [x] 5.2 实现 `backend/app/services/llm/base_adapter.py`：抽象基类 `LLMProviderAdapter`，方法 `build_request(messages, options) -> httpx.Request`、`parse_stream_chunk(line: bytes) -> tuple[delta: str, finish_reason: str | None]`
- [x] 5.3 实现 `backend/app/services/llm/openai_adapter.py`：`OpenAICompatibleAdapter`，构造 `POST {base_url}/v1/chat/completions`，stream chunk 解析 `data: {...}` SSE 行
- [x] 5.4 实现 `backend/app/services/llm/factory.py`：`get_adapter(provider_type: str) -> LLMProviderAdapter`，注册 `openai -> OpenAICompatibleAdapter`，对未知 type 抛 `ValueError`
- [x] 5.5 实现 `backend/app/api/llm.py` 路由：`GET/POST/PUT/DELETE /api/llm/providers`；`POST /api/llm/chat` 同步调用（`stream=False`）；`POST /api/llm/chat/stream` 返回 `StreamingResponse(media_type="text/event-stream")`
- [x] 5.6 SSE 事件格式：每个 chunk `data: {"delta":"...","finish_reason":null}\n\n`，结束 `data: {"delta":"","finish_reason":"stop"}\n\n`，错误 `data: {"error":"..."}\n\n`
- [x] 5.7 在 config.json 的 `llm_providers` 字段读写 Provider；调用后追加历史到 `history.json` 的 `llm_calls` 数组（最多 100 条，含 token usage）
- [x] 5.8 验证：用 DeepSeek 或 OpenAI 真实 api_key 调用 `/api/llm/chat` 同步返回，再调用 `/chat/stream` 通过 curl 看到 SSE 增量

### 前端

- [x] 5.9 创建 `frontend/src/stores/llm.ts`：providers 列表、当前选中 provider、messages、流式响应文本
- [x] 5.10 创建 `frontend/src/views/LlmPlayground.vue`：左侧 Provider 列表（增删改 + api_key 掩码显示），右侧聊天面板
- [x] 5.11 聊天面板：messages 列表（user/assistant/system），消息编辑用 Monaco，底部发送按钮 + stream 开关
- [x] 5.12 流式调用使用 `EventSource('/api/llm/chat/stream?...')` 或 `fetch + ReadableStream`，增量文本通过 `Monaco.applyEdits` 追加到 assistant 消息块
- [x] 5.13 流式结束展示 token usage，流式中断显示「已中断」状态
- [x] 5.14 「LLM 历史」标签页：列出最近 100 条调用，点击查看完整 messages 与响应
- [x] 5.15 验证：开启 stream 调用，前端看到逐字增量；关闭 stream 调用，一次性返回完整内容

## 6. 通用前端框架与布局

- [x] 6.1 配置 `frontend/src/router/index.ts`：路由 `/http`、`/mcp`、`/llm`、`/history`，默认重定向到 `/http`
- [x] 6.2 创建 `frontend/src/layouts/MainLayout.vue`：顶部导航（HTTP / MCP / LLM / 历史四个 tab）+ Element Plus Container 布局
- [x] 6.3 创建 `frontend/src/views/HistoryView.vue`：聚合 http_calls / mcp_calls / llm_calls 三个 tab
- [x] 6.4 全局引入 Element Plus 与暗色主题跟随系统，配置 Pinia 持久化插件（仅 dev，生产环境后端持久化）
- [x] 6.5 配置 Monaco Editor worker：通过 `vite-plugin-monaco-editor` 或 `?worker` 导入，确保打包后 worker 路径正确

## 7. 打包与发布

- [x] 7.1 创建 `backend/launcher.spec` PyInstaller spec：`onefile=True`，`add_data=('frontend/dist', 'frontend/dist')`，hiddenimports 包含 `uvicorn.logging`、`mcp.*`、`httpx.*`
- [x] 7.2 实现 `backend/app/resources.py`：`resolve_static_path()` 在 `sys._MEIPASS` 与开发路径之间自动切换
- [x] 7.3 在 `backend/main.py` 中检测 `APP_ENV`，未设置时默认 `production`，生产模式自动调用 `find_available_port` 与 `webbrowser.open_new_tab`
- [x] 7.4 执行 `cd frontend && npm run build` 生成 `frontend/dist`
- [x] 7.5 执行 `cd backend && pyinstaller launcher.spec` 生成 `dist/api-tool.exe`
- [ ] 7.6 验证：在干净 Windows 机器（无 Python）双击 `api-tool.exe`，2-5 秒内自动打开浏览器并展示 HTTP 工作台
- [ ] 7.7 验证：连续启动两次（占用首次端口），第二次自动切换到下一可用端口
- [x] 7.8 在 `README.md` 中补充：开发启动命令、打包命令、配置文件路径说明

## 8. 端到端验收

- [x] 8.1 HTTP 场景：发送 GET、POST(JSON)、POST(form-data) 三种请求均成功返回并展示
- [x] 8.2 HTTP 历史：发送 3 次请求后历史列表正确展示，重启应用后历史仍存在
- [ ] 8.3 MCP 场景：添加 MCP Server → 测试连接 → 列出工具 → 调用工具，全流程通过
- [ ] 8.4 LLM 场景：添加 OpenAI Compatible Provider → 同步调用 → 流式调用，均返回正确内容
- [x] 8.5 LLM Adapter：模拟 `provider_type=custom` 调用，工厂抛出明确错误
- [ ] 8.6 应用外壳：双击 exe 自动打开浏览器；同局域网其他设备无法访问；首次启动自动创建 `~/.api-tool/` 配置目录
