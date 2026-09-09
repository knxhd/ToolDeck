## 新增需求

### 需求:HTTP 请求构造器
系统必须允许用户构造完整的 HTTP 请求，包括 Method、URL、Query Params、Headers、Body 和 Auth 设置。

#### 场景:用户选择 HTTP Method
- **当** 用户点击 Method 下拉菜单
- **那么** 系统显示 GET、POST、PUT、PATCH、DELETE、HEAD、OPTIONS 七种方法供选择
- **当** 用户选择某种方法
- **那么** 该方法显示在 URL 输入框左侧

#### 场景:用户输入 URL
- **当** 用户在 URL 输入框输入地址
- **那么** 系统允许完整 URL 输入（含协议），也允许仅路径（自动补全 http:// 前缀）

#### 场景:用户添加 Query Params
- **当** 用户切换到 Params Tab
- **那么** 系统显示键值对编辑器，允许添加、删除、启用/禁用参数
- **当** 用户编辑 Query Params
- **那么** URL 输入框中的 query string 实时更新

### 需求:Body 类型支持
系统必须支持五种 Body 类型：none、raw（JSON/TXT）、form-data、x-www-urlencoded、binary。

#### 场景:用户选择 none Body
- **当** 用户选择 none 类型
- **那么** 系统不发送请求体

#### 场景:用户选择 raw Body
- **当** 用户选择 raw 类型
- **那么** 系统提供多行文本编辑器，支持 JSON 和 TXT 子类型切换
- **当** 用户选择 JSON 子类型
- **那么** 自动设置 Content-Type 为 application/json

#### 场景:用户选择 form-data Body
- **当** 用户选择 form-data 类型
- **那么** 系统提供字段编辑器，支持 text 和 file 两种字段类型
- **当** 用户添加 file 类型字段
- **那么** 系统允许选择本地文件，自动编码为 multipart/form-data

#### 场景:用户选择 x-www-urlencoded Body
- **当** 用户选择 x-www-urlencoded 类型
- **那么** 系统提供键值对编辑器，自动 URL 编码后发送

#### 场景:用户选择 binary Body
- **当** 用户选择 binary 类型
- **那么** 系统允许选择本地文件，以二进制方式发送

### 需求:Auth 快捷注入
系统必须支持四种认证方式的快捷注入：none、Bearer Token、Basic Auth、API Key。

#### 场景:用户选择 Bearer Token 认证
- **当** 用户在 Auth Tab 选择 Bearer Token 类型
- **那么** 系统显示 Token 输入框
- **当** 用户输入 Token 并发送请求
- **那么** 自动添加 Header: Authorization: Bearer <token>

#### 场景:用户选择 Basic Auth 认证
- **当** 用户在 Auth Tab 选择 Basic Auth 类型
- **那么** 系统显示 Username 和 Password 输入框
- **当** 用户输入凭据并发送请求
- **那么** 自动添加 Header: Authorization: Basic <base64编码>

#### 场景:用户选择 API Key 认证
- **当** 用户在 Auth Tab 选择 API Key 类型
- **那么** 系统显示 Key Name、Key Value 和位置选择（Header / Query Param）
- **当** 用户设置完成并发送请求
- **那么** 根据位置自动注入到 Header 或 URL Query

### 需求:发送 HTTP 请求
系统必须通过 FastAPI 后端代理发送 HTTP 请求，绕过浏览器 CORS 限制。

#### 场景:发送普通 HTTP 请求
- **当** 用户点击 Send 按钮
- **那么** 前端 POST /api/request，后端用 httpx 发送请求
- **当** 请求完成
- **那么** 后端返回包含 status、headers、body、time_ms、size_bytes、content_type 的 JSON

#### 场景:发送流式 HTTP 请求
- **当** 用户点击 Send 按钮且开启流式选项
- **那么** 前端 POST /api/request/stream，后端返回 StreamingResponse
- **当** 上游是 SSE 响应
- **那么** 后端逐帧透传原始 SSE 帧

#### 场景:请求超时处理
- **当** 请求超过 30 秒未完成
- **那么** 后端返回超时错误，前端显示超时提示
