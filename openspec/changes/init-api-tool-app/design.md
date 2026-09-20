## 上下文

本项目从零构建，无遗留代码约束。最终交付物是 Windows 平台单文件可执行程序（后续可扩展 Mac）。开发期前后端分离运行（Vite dev server + FastAPI uvicorn），生产期前端构建产物由 FastAPI 静态托管。应用核心是把 Postman 的 HTTP 调试能力、MCP Streamable HTTP 客户端、OpenAI 兼容大模型调用三者整合在同一 Web UI 中。

技术约束：
- 仅监听 `127.0.0.1`，不暴露公网/局域网
- MCP 仅支持 Streamable HTTP 传输方式（不支持 stdio/SSE 旧协议）
- 大模型优先 OpenAI Compatible，其余厂商通过 Adapter 扩展
- 单进程：FastAPI 同时承担 API 服务 + 静态资源托管 + 启动浏览器

## 目标 / 非目标

**目标：**
- 双击 exe 即启动服务并自动打开浏览器访问应用
- HTTP 工作台覆盖 Postman 基础能力：方法/URL/Header/Body/Params/历史/响应展示
- MCP 客户端完成 initialize → list tools → call tool 全流程，结果可读
- 大模型调用支持 OpenAI Compatible `/v1/chat/completions`，含 SSE 流式解析
- Provider Adapter 接口允许后续扩展 Anthropic、智谱等非 OpenAI 协议
- 流式响应通过 SSE 推送到前端，前端实时渲染增量内容
- 所有配置（请求历史、MCP 服务器、LLM Provider）持久化到本地 JSON 文件

**非目标：**
- 不做云同步、账号体系、团队协作
- 不做 MCP stdio / SSE 旧协议支持
- 不支持非 OpenAI 协议厂商的官方 SDK 直连（仅通过 Adapter 转换为 OpenAI 兼容格式）
- 不内置大模型推理能力，只做调用代理
- 不做复杂自动化测试集合（Collection Runner），仅做单请求调试
- 不做请求性能压测、并发对比等高级功能

## 决策

### 1. 单进程 FastAPI 托管前端静态资源

**选择：** FastAPI 通过 `StaticFiles` 挂载 `frontend/dist`，单进程同时处理 API 与静态资源。

**替代方案：**
- Electron + Vue：体积大、用户不喜欢重框架（用户偏好明确）
- Tauri + Vue：需 Rust 工具链，与 Python 后端技术栈割裂
- 双进程（Vite + FastAPI）：生产环境部署复杂，单 exe 打包困难

**理由：** Python 单进程最简单，PyInstaller 打包成单 exe 直接双击运行；FastAPI 的 `StaticFiles` 足够托管 SPA，HTML5 history 路由通过 catch-all fallback 处理。

### 2. MCP 仅使用 Streamable HTTP

**选择：** 通过 Python MCP SDK 的 `streamable_http_client` 连接 MCP Server，不实现 stdio / 旧 SSE 协议。

**替代方案：**
- 自行基于 HTTP + JSON-RPC 封装：可控但重复造轮，协议升级成本高
- 同时支持 stdio：需要进程管理、跨平台 spawn，复杂度倍增

**理由：** 用户明确仅需 Streamable HTTP；官方 SDK 已封装 initialize/tools.list/tools.call 流程，直接复用最稳定。

### 3. LLM 统一转换为 OpenAI Compatible 格式

**选择：** 所有 Provider 在 Adapter 层把请求/响应统一为 OpenAI 格式（`messages`、`tools`、`stream`），后端只面向一种内部协议开发。OpenAI Compatible Provider 直接 passthrough。

**替代方案：**
- 每个 Provider 独立实现调用逻辑：业务代码会充斥 `if provider ==` 分支
- 直接调厂商 SDK：被 SDK 绑死，新增 Provider 成本高

**理由：** OpenAI 格式已成为事实标准（DeepSeek、智谱、Moonshot、通义均提供兼容端点），统一抽象后端只需实现一次流式解析。

### 4. 前端使用 Monaco Editor 处理 Body / 响应

**选择：** Monaco Editor 处理 JSON Body 编辑、响应高亮、流式增量渲染。

**替代方案：** CodeMirror、textarea、Element Plus Input：JSON 高亮/折叠能力弱。

**理由：** Postman 风格工具中编辑器是核心组件，Monaco 提供最佳 JSON 体验；流式响应通过 `Monaco.editor.getModel().applyEdits()` 增量追加。

### 5. 流式传输用 SSE 而非 WebSocket

**选择：** 后端 `StreamingResponse` (media_type `text/event-stream`) 推送，前端 `EventSource` 消费。

**替代方案：** WebSocket：双向通信但本场景只需单向推送，多余的复杂度。

**理由：** SSE 单向、自动重连、浏览器原生支持，正好契合 LLM token 流式 + MCP 长任务调用的场景。

### 6. 配置持久化用本地 JSON 文件

**选择：** `~/.api-tool/config.json` + `~/.api-tool/history.json`，无数据库。

**替代方案：** SQLite：单文件 exe 部署仍需引入驱动，过度设计。

**理由：** 配置量小（几十条历史、几个 Provider），JSON 读写简单、便于用户备份/迁移。

## 风险 / 权衡

- **[单 exe 启动慢]** PyInstaller 打包后冷启动 2-5 秒（解压临时目录） → 接受，展示启动 splash 文本；后续可考虑 onedir 模式
- **[MCP Server 不可达]** 用户配置的 MCP 端点可能离线 → 连接前必须先做健康检查（GET / 或 initialize 探测），失败时 UI 明确提示
- **[LLM 流式中断]** 网络抖动导致 SSE 中断 → 前端 EventSource 自动重连仅对幂等请求有意义，对话流式不重试，UI 显示「已中断」状态
- **[Provider Adapter 协议漂移]** OpenAI 格式后续可能扩展字段 → Adapter 接口用 Pydantic Model 定义，字段变更集中在一处
- **[Monaco Editor 包体积]** Monaco 前端打包后较大（~3MB）→ Vite chunk 拆分，按需加载 worker
- **[端口冲突]** 8765 端口被占用 → 启动时检测并自动递增端口（8765→8766→…→8775），打开浏览器使用实际端口
- **[CORS]** 开发期前后端分离运行 → 开发环境 FastAPI 启用 `CORSMiddleware`，生产环境同源无需 CORS

## 迁移计划

首次构建无迁移。后续版本演进时：
- `~/.api-tool/config.json` 增加 `version` 字段，启动时按版本号迁移
- Provider Adapter 接口变更通过 `protocol_version` 标识，旧 Provider 报错并提示升级

## 开放问题

- 是否需要支持 MCP resources / prompts 端点？当前仅 tools，需用户确认后再扩展
- 大模型 Function Calling 是否需要在第一阶段支持？当前 spec 仅覆盖 chat completion，tools 调用留待后续
- 是否提供暗色主题？Element Plus 支持，默认跟随系统
