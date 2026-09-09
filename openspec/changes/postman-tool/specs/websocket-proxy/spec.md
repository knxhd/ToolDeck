## 新增需求

### 需求:WebSocket 双向通信
系统必须提供 WebSocket 代理端点，支持前端与目标 WebSocket Server 的双向实时消息通信。

#### 场景:建立 WebSocket 连接
- **当** 用户在请求构造器中选择 WebSocket 类型并输入 ws:// 或 wss:// URL
- **那么** 前端连接到后端 WS /api/ws?url=<目标URL>
- **当** 后端收到连接请求
- **那么** 后端同时连接到目标 WebSocket Server

#### 场景:发送 WebSocket 消息
- **当** 用户在消息输入框输入文本并点击发送
- **那么** 前端通过 WebSocket 发送消息给后端
- **当** 后端收到消息
- **那么** 后端将消息转发给目标 WebSocket Server

#### 场景:接收 WebSocket 消息
- **当** 目标 WebSocket Server 推送消息
- **那么** 后端将消息转发给前端
- **当** 前端收到消息
- **那么** 消息实时显示在消息列表中，标记为"received"

#### 场景:连接状态显示
- **当** WebSocket 连接状态变化（连接中/已连接/已断开/错误）
- **那么** UI 实时显示当前连接状态
- **当** 连接断开
- **那么** UI 提示用户，提供手动重连按钮

#### 场景:断开 WebSocket 连接
- **当** 用户点击 Disconnect 按钮
- **那么** 前端关闭与后端的 WebSocket 连接
- **当** 后端检测到前端连接关闭
- **那么** 后端同时关闭与目标 WebSocket Server 的连接
