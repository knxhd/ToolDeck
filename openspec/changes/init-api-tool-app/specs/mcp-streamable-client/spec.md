## 新增需求

### 需求:MCP Server 连接管理
系统必须允许用户通过 Streamable HTTP URL 添加、编辑、删除、测试 MCP Server 连接。连接信息必须持久化到 `~/.api-tool/config.json` 的 `mcp_servers` 字段。每个 MCP Server 配置必须包含 name、url、可选 headers（鉴权用）。添加后必须提供「测试连接」按钮，调用 initialize 探测连通性。

#### 场景: 添加 MCP Server
- **当** 用户填入 name `local`、url `http://127.0.0.1:8001/mcp`，点击保存
- **那么** 配置写入 config.json，MCP Server 列表 UI 立即显示该项

#### 场景: 测试连接失败
- **当** 用户对某 MCP Server 点击「测试连接」且端点不可达
- **那么** UI 显示红色错误提示「无法连接：<错误信息>」，不删除配置

### 需求:MCP Streamable HTTP 调用
系统必须通过 Python MCP SDK 的 `streamable_http_client` 与 MCP Server 通信，仅支持 Streamable HTTP 传输方式，禁止实现 stdio 或旧版 SSE 传输。必须按顺序完成 `initialize` → `tools/list` → `tools/call` 协议流程。

#### 场景: 初始化握手
- **当** 用户选中某 MCP Server 并点击「连接」
- **那么** 后端调用 `initialize`，成功后前端展示协议版本、Server 名称与版本

#### 场景: 仅支持 Streamable HTTP
- **当** 用户尝试配置 stdio 类型 MCP Server
- **那么** UI 禁止保存，提示「仅支持 Streamable HTTP 传输方式」

### 需求:MCP 工具列表展示
系统必须在 MCP Server 连接成功后调用 `tools/list`，以可折叠列表展示所有工具的 name、description、inputSchema。inputSchema 必须以 JSON 形式可视化，方便用户理解参数结构。

#### 场景: 列出工具
- **当** MCP Server initialize 成功
- **那么** 后端调用 `tools/list`，前端展示工具卡片列表，每张卡片包含 name、description、参数 schema 折叠区

### 需求:MCP 工具调用
系统必须允许用户对选中工具填写参数并调用 `tools/call`，结果展示在结果面板。参数编辑必须基于 inputSchema 自动生成表单（优先）或 JSON 编辑器（兜底）。调用结果若是 `text` 类型必须直接展示文本，若是 `resource` 或 `image` 类型必须展示类型与摘要并允许复制原始内容。

#### 场景: 调用工具成功
- **当** 用户对 `echo` 工具填入参数 `{"message":"hello"}`，点击调用
- **那么** 后端调用 `tools/call`，结果面板展示返回内容，并记录调用历史

#### 场景: 工具调用错误
- **当** MCP Server 返回 `isError: true` 或抛出异常
- **那么** 结果面板红色展示错误内容，不崩溃整个连接

### 需求:MCP 调用历史
系统必须把每次 `tools/call` 的 server name、tool name、参数、结果摘要、时间戳记录到 `~/.api-tool/history.json` 的 `mcp_calls` 数组，最多保留 100 条。

#### 场景: 查看 MCP 调用历史
- **当** 用户切到「MCP 历史」标签
- **那么** 列出最近 100 次 MCP 调用，点击任一条可查看完整参数与结果
