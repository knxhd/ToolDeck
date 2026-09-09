## 1. 项目初始化 & 后端基础

- [x] 1.1 创建项目目录结构（backend/、frontend/、requirements.txt）
- [x] 1.2 安装依赖（fastapi、uvicorn、httpx、pydantic）
- [x] 1.3 创建 FastAPI 应用入口 main.py，配置 CORS 中间件
- [x] 1.4 实现静态文件 serve（frontend/ 目录下的 HTML 直接返回）

## 2. 后端 HTTP 请求代理

- [x] 2.1 定义请求/响应 Pydantic 模型（RequestPayload、ResponsePayload、AuthConfig、FormField）
- [x] 2.2 实现 Auth 注入逻辑：将 AuthConfig 转换为 HTTP Headers（Bearer / Basic / API Key）
- [x] 2.3 实现 Body 编码逻辑：根据 body_type 构造 httpx 请求体（raw / form-data / x-www-urlencoded / binary）
- [x] 2.4 实现 POST /api/request 端点：接收请求、发 httpx 调用、采集元信息、返回 JSON
- [x] 2.5 添加请求超时处理（30 秒）和错误捕获

## 3. 后端 SSE 流式透传

- [x] 3.1 实现 POST /api/request/stream 端点
- [x] 3.2 实现上游 SSE 响应逐帧透传逻辑（StreamingResponse + httpx.stream）
- [x] 3.3 实现上游非 SSE 响应包装为 SSE 帧（data: {"type":"frame","data":"..."} + data: {"type":"done"}）
- [x] 3.4 实现流结束时的 finally 块确保 data: {"type":"done"} 一定发送

## 4. 后端 WebSocket 代理

- [x] 4.1 实现 WS /api/ws?url=<target> 端点
- [x] 4.2 实现前端 ↔ FastAPI ↔ 目标 WebSocket Server 的双向转发逻辑
- [x] 4.3 实现连接状态管理（连接中/已连接/已断开）和错误处理

## 5. 前端基础框架 & 多 Tab 工作区

- [x] 5.1 创建 index.html，引入 Vue 3 CDN + Tailwind CSS CDN
- [x] 5.2 实现 Vue 应用入口和全局响应式状态对象
- [x] 5.3 实现多 Tab 管理组件（创建/切换/关闭 Tab，Tab 独立状态隔离）
- [x] 5.4 实现 Tab 标题自动更新逻辑（从 URL 提取域名）

## 6. 前端请求构造器

- [x] 6.1 实现 Method 下拉菜单 + URL 输入框 + Params Tab（键值对编辑器）
- [x] 6.2 实现 Headers Tab（键值对编辑器）
- [x] 6.3 实现 Auth Tab（Bearer / Basic / API Key 三种认证方式的 UI 和逻辑）
- [x] 6.4 实现 Body Tab（none / raw / form-data / x-www-urlencoded / binary 五种类型切换）
- [x] 6.5 实现 form-data 文件选择和 base64 编码
- [x] 6.6 实现 Send 按钮：构造请求体 → 调用 /api/request 或 /api/request/stream → 处理响应
- [x] 6.7 实现 WebSocket 连接/发送/断开 UI 组件

## 7. 前端结果展示 & 格式化

- [x] 7.1 实现响应元信息栏（状态码、状态文本、耗时、大小）
- [x] 7.2 实现格式化 Tab 切换组件（Raw / JSON / HTML / XML / TXT）
- [x] 7.3 实现 JSON 美化缩进（JSON.stringify + 2 空格）
- [x] 7.4 实现 HTML iframe 渲染预览
- [x] 7.5 实现 XML 美化缩进
- [x] 7.6 实现响应 Headers Tab 查看

## 8. 前端 SSE 解析器

- [x] 8.1 实现 SSEParser 接口（onFrame / getAccumulated / reset / isComplete / name / description）
- [x] 8.2 实现 OpenAIParser（解析 choices[0].delta.content，累积拼接）
- [x] 8.3 实现解析器注册机制（Map<string, SSEParser>）
- [x] 8.4 实现 SSE 帧接收逻辑：用 fetch + ReadableStream 读取后端 SSE，逐帧解析
- [x] 8.5 实现原始帧视图实时追加显示
- [x] 8.6 实现解析器下拉选择器 + 累积视图实时更新
- [x] 8.7 实现所有解析器同时接收帧、切换下拉只改变显示

## 9. 前端历史 & Collection

- [x] 9.1 实现 localStorage 读写工具函数（history / collections 两个键）
- [x] 9.2 实现自动历史记录：每次 Send 后追加到 history（限制最近 50 条）
- [x] 9.3 实现侧边栏 History 面板（列表显示 + 点击重放 + 清空按钮）
- [x] 9.4 实现侧边栏 Collection 面板（创建/重命名/删除 Collection）
- [x] 9.5 实现保存请求到 Collection（选择已有或新建）
- [x] 9.6 实现从 Collection 打开请求（创建新 Tab + 预填充）
- [x] 9.7 实现 Collection 内请求的重命名和删除

## 10. 集成测试 & 验证

- [x] 10.1 启动 FastAPI 服务，验证首页可访问
- [x] 10.2 测试 HTTP GET/POST/PUT/DELETE 请求（普通 JSON 响应）
- [x] 10.3 测试 form-data 文件上传
- [x] 10.4 测试 SSE 流式响应（用 FastAPI 内置测试 SSE 端点或 OpenAI Mock）
- [x] 10.5 测试 OpenAI 解析器累积视图
- [x] 10.6 测试 WebSocket 双向通信（用 ws://echo.websocket.org）
- [x] 10.7 测试多 Tab 并发请求
- [x] 10.8 测试历史记录和 Collection 的 localStorage 持久化（刷新页面后数据保留）
