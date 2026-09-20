## 新增需求

### 需求:LLM Provider 配置
系统必须允许用户管理 LLM Provider 列表，每个 Provider 配置必须包含 name、base_url、api_key、model、provider_type（`openai` / `anthropic` / `custom`）。配置必须持久化到 `~/.api-tool/config.json` 的 `llm_providers` 字段。api_key 在持久化时必须明文存储（本地工具，用户自负责任），UI 展示时必须掩码（仅显示前后各 4 字符）。

#### 场景: 添加 OpenAI Compatible Provider
- **当** 用户填入 name `deepseek`、base_url `https://api.deepseek.com`、provider_type `openai`、api_key、model `deepseek-chat`，点击保存
- **那么** Provider 写入 config.json，列表 UI 显示该项，api_key 列展示为 `sk-1***abcd`

#### 场景: 编辑 Provider
- **当** 用户修改某 Provider 的 model 字段并保存
- **那么** config.json 同步更新，UI 反映新值

### 需求:OpenAI Compatible Chat 调用
系统必须对 `provider_type = openai` 的 Provider 直接以 OpenAI 格式调用 `POST {base_url}/v1/chat/completions`，请求体包含 model、messages、stream、可选 temperature。响应必须正确解析 `choices[0].delta.content` 与 `choices[0].message.content`。

#### 场景: 同步调用 OpenAI Compatible
- **当** 用户选择 Provider `deepseek`，填入 messages，关闭 stream，点击发送
- **那么** 后端通过 httpx 同步调用，响应面板展示完整 message.content 与 token usage

#### 场景: 流式调用 OpenAI Compatible
- **当** 用户开启 stream 选项并点击发送
- **那么** 后端通过 StreamingResponse 将每个 chunk 的 delta.content 实时推送到前端，Monaco Editor 增量追加

### 需求:Provider Adapter 抽象
系统必须定义 `LLMProviderAdapter` 抽象基类，包含 `build_request(messages, options) -> httpx.Request` 与 `parse_stream_chunk(line) -> str` 两个方法。OpenAI Compatible Provider 使用 `OpenAICompatibleAdapter` 直接 passthrough。非 OpenAI 协议厂商（如 Anthropic）必须实现自己的 Adapter 将其请求/响应转换为内部 OpenAI 格式。Adapter 必须通过工厂函数 `get_adapter(provider_type) -> Adapter` 获取。

#### 场景: 使用 OpenAI Compatible Adapter
- **当** Provider `provider_type = openai`
- **那么** 工厂返回 `OpenAICompatibleAdapter`，请求与响应按 OpenAI 格式直通处理

#### 场景: 注册新 Adapter
- **当** 后续添加 Anthropic Provider（provider_type = `anthropic`）
- **那么** 必须实现 `AnthropicAdapter` 并在工厂注册，后端业务代码无需修改

### 需求:流式响应 SSE 推送
系统必须通过 FastAPI `StreamingResponse(media_type="text/event-stream")` 把 LLM 流式响应逐 chunk 推送到前端。每个 SSE 事件 data 字段必须是 JSON，包含 `delta`（增量文本）和 `finish_reason`（结束时非空）。前端必须使用 `EventSource` 接收并实时渲染到 Monaco Editor。

#### 场景: SSE 增量渲染
- **当** 后端推送 `data: {"delta":"hello"}\n\n`
- **那么** 前端 Monaco Editor 在当前光标处追加 `hello`

#### 场景: 流式结束
- **当** 后端推送 `data: {"delta":"","finish_reason":"stop"}\n\n` 并关闭连接
- **那么** 前端停止追加，标记流式完成，展示 token usage

#### 场景: 流式中断
- **当** 上游 LLM 连接中断
- **那么** 后端推送 `data: {"error":"..."}` 事件并关闭 SSE，前端显示「已中断」

### 需求:LLM 调用历史
系统必须把每次 LLM 调用（provider、model、messages 摘要、响应摘要、token usage、时间戳）记录到 `~/.api-tool/history.json` 的 `llm_calls` 数组，最多保留 100 条。

#### 场景: 查看 LLM 历史
- **当** 用户切到「LLM 历史」标签
- **那么** 列出最近 100 次调用，点击可查看完整 messages 与响应
