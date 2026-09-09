## 为什么

Postman 是最流行的 API 调试工具，但存在以下痛点：(1) 商业许可费用高；(2) 对 MCP Streamable HTTP 等新兴协议缺乏原生支持；(3) SSE 流式接口的查看能力薄弱，无法像 OpenAI Chat Completions 那样直观地查看累积的完整文本；(4) 闭源、云同步、部分功能需付费解锁。需要一个自托管、可扩展的本地 API 调试工具。

## 变更内容

- 新增：基于 FastAPI + 原生 HTML/JS 的自托管 API 调试工具，支持 HTTP、WebSocket、SSE、MCP Streamable HTTP 四种协议
- 新增：多 Tab 工作区，同时编辑/发送多个请求
- 新增：完整 Body 类型支持（none / raw / form-data / x-www-urlencoded / binary）
- 新增：Auth 快捷注入（Bearer / Basic / API Key）
- 新增：SSE 流式响应的协议解析视图，支持下拉切换解析器（先做 OpenAI，架构预留扩展位），实时累积显示完整文本
- 新增：响应格式化 Tab 切换（JSON / HTML / XML / TXT）
- 新增：localStorage 自动历史记录 + 可保存的 Collection（命名分组）
- 新增：WebSocket 双向通信代理端点

## 功能 (Capabilities)

### 新增功能
- `http-request`: HTTP 请求构造与发送，含 Method、URL、Query Params、Headers、Body（全类型）、Auth 快捷注入
- `websocket-proxy`: WebSocket 双向通信代理，前端 WS → FastAPI WS → 目标 WS Server
- `sse-streaming`: SSE 流式响应透传与实时帧显示
- `sse-protocol-parsers`: SSE 协议解析器框架，下拉切换，先实现 OpenAI 协议，预留扩展位（千问等）
- `response-formatting`: 响应结果多格式格式化展示（JSON / HTML / XML / TXT）
- `multi-tab-workspace`: 多 Tab 工作区，独立状态管理
- `history-collection`: localStorage 历史记录 + 可保存 Collection

### 修改功能
无

## 影响

- 新增 FastAPI 后端应用（Python，依赖 httpx、uvicorn、pydantic）
- 新增原生 HTML/JS 前端（无构建步骤，Vue 3 CDN 模式）
- 新增 WebSocket 代理端点 `/api/ws`
- 新增 HTTP 请求端点 `/api/request` 和 `/api/request/stream`
- 无数据库依赖（历史和 Collection 存前端 localStorage）
- 无破坏性变更（全新项目）
