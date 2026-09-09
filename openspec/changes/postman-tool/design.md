## 上下文

需要构建一个自托管的 API 调试工具，替代 Postman。核心挑战包括：(1) 浏览器 CORS 限制导致必须有后端代理；(2) 不同协议（HTTP/WS/SSE/MCP Streamable HTTP）需要不同的传输方式；(3) SSE 流式响应需要前端实时解析并累积显示；(4) 多 Tab 状态管理、历史记录持久化等前端复杂度。

项目当前为空目录，只有 OpenSpec 配置，无现有代码或架构约束。

## 目标 / 非目标

**目标：**
- 支持 HTTP、WebSocket、SSE、MCP Streamable HTTP 四种协议
- SSE 响应支持协议解析视图（下拉切换），实时累积显示
- 多 Tab 工作区，每个 Tab 独立状态
- localStorage 历史记录 + 可保存 Collection
- 完整 Body 类型和 Auth 快捷注入
- 响应多格式（JSON/HTML/XML/TXT）格式化
- 架构可扩展（SSE 解析器、Body 类型等）

**非目标：**
- Pre-request / Test scripts（类似 Postman 的脚本执行）
- Cookie 管理面板
- 环境变量 `{{base_url}}`
- 千问等非 OpenAI 的 SSE 解析器（架构预留位，后续扩展）
- 后端持久化历史（纯前端 localStorage）
- MCP 专用 UI（按普通 HTTP 客户端处理）
- 二进制响应预览

## 决策

### 决策 1：前端技术栈 — Vue 3 CDN 模式而非原生 JS

**理由：** 多 Tab 状态管理、响应式数据绑定、组件化等需求，原生 JS 实现会非常繁琐。Vue 3 CDN 模式免构建，FastAPI 直接 serve 静态文件，开发体验接近原生但有组件化能力。

**替代方案：**
- 原生 JS：零依赖但多 Tab 状态管理痛苦
- React + Vite：需要构建步骤，增加复杂度
- Vue 3 SFC + Vite：同样需要构建

### 决策 2：后端 SSE 透传策略 — 统一 SSE 通道

**理由：** 无论上游是真正的 SSE 还是普通 HTTP 响应，后端统一用 `StreamingResponse(text/event-stream)` 返回。上游 SSE 逐帧透传原始帧；上游非 SSE 响应包装成 SSE 帧。前端统一用 `EventSource` 或 `fetch+ReadableStream` 处理，不分支。

**SSE 帧格式：**
```
data: {"type":"frame","data":"<原始payload字符串>"}
data: {"type":"done"}
```

**替代方案：**
- 上游 SSE 走 EventSource，上游普通 HTTP 走 fetch：前端代码分支多，状态同步复杂
- 后端解析 SSE 协议后给前端：前端无法拿到原始帧，丢失调试能力

**风险：** 非流式响应也被"伪造"成 SSE，前端需要处理 `type=frame` 和 `type=done` 两种帧类型。

### 决策 3：SSE 协议解析器 — 前端实现，接口抽象

**理由：** 解析器只依赖 SSE payload 字符串，在前端实现避免后端协议耦合，切换解析器无需重发请求，新增解析器只需前端加一个类。

**解析器接口：**
```javascript
class SSEParser {
  name: string                    // 显示名称
  description: string             // 描述
  onFrame(payload: string): void  // 收到一帧
  getAccumulated(): string        // 取累积结果
  reset(): void                   // 重置
  isComplete(): boolean           // 是否完成
}
```

**前端收到 SSE 帧时：** 同时喂给所有已注册解析器，下拉菜单控制显示哪个解析器的累积结果。

**替代方案：**
- 后端解析后给前端：切换解析器要重发请求，前端无法拿到原始帧
- 后端同时做原始帧透传和解析结果：后端复杂度高，响应体积翻倍

### 决策 4：WebSocket 代理 — 独立 WS 端点

**理由：** 浏览器无法直接发起跨域 WebSocket 连接（有 CORS 限制），必须有后端代理。HTTP 和 WS 是不同协议，需要不同的传输通道，独立端点更清晰。

**端点：** `WS /api/ws?url=ws://target.example.com`

**替代方案：**
- 在 HTTP 端点里协商升级：FastAPI 可以处理，但增加复杂度
- 前端直接连目标：CORS 限制不允许

### 决策 5：历史和 Collection — 纯前端 localStorage

**理由：** MVP 阶段不需要跨设备同步，localStorage 足够。后端纯代理，不做数据持久化，职责清晰。后续需要服务端持久化时再加 SQLite。

**数据结构：**
```javascript
// 历史记录
history: [
  { id, url, method, headers, body, body_type, auth, timestamp }
]

// Collection
collections: [
  {
    id, name,
    requests: [
      { id, name, url, method, headers, body, body_type, auth }
    ]
  }
]
```

### 决策 6：后端不做协议解析，只做传输层

**后端职责边界：**
- CORS 绕过 ✅
- Body 编码（form-data / x-www-urlencoded）✅
- SSE 透传 / 包装 ✅
- 响应元信息采集（状态码、时长、大小）✅
- SSE 协议解析 ❌（前端做）
- 响应格式化 ❌（前端做）
- 请求历史存储 ❌（前端做）

**理由：** 后端保持简单，职责单一，协议解析和格式化是纯计算，前端做更灵活且可扩展。

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|----------|
| SSE 透传时上游断连，前端不知道 | 后端在 StreamResponse 的 finally 里发 `data: {"type":"done"}` 或错误帧 |
| form-data 文件上传，前端要把文件转 base64 传给后端 | 后端接收 base64 内容，用 httpx 的 files 参数构造 multipart，前端用 FileReader |
| WebSocket 代理的错误恢复 | 前端显示连接状态，重连逻辑由前端控制 |
| localStorage 容量限制（~5MB） | 历史记录限制最近 50 条，Collection 限制每个 < 10 条请求 |
| Vue 3 CDN 模式下组件间通信 | 使用响应式全局状态对象（reactive + provide/inject 或直接模块级变量） |
| SSE 同时喂给所有解析器可能的性能问题 | OpenAI 解析器很轻量（只是字符串拼接），后续解析器复杂时再优化 |

## 开放问题

- 无。所有关键决策已在探索阶段对齐。
