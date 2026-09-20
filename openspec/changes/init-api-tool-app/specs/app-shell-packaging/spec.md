## 新增需求

### 需求:应用入口与启动流程
系统必须提供 `api-tool.exe` 入口，双击后按以下顺序执行：1) 检测可用端口（默认 8765，被占用则递增到 8775 上限）；2) 启动 uvicorn 托管 FastAPI 应用；3) 通过 `webbrowser.open_new_tab(url)` 打开默认浏览器；4) 进入主事件循环。启动期间必须向 stdout 输出日志便于排错。

#### 场景: 默认启动
- **当** 用户双击 `api-tool.exe`
- **那么** 进程在 127.0.0.1:8765 启动 FastAPI，2 秒内打开浏览器访问 `http://127.0.0.1:8765`

#### 场景: 端口冲突自动重试
- **当** 8765 端口被占用
- **那么** 进程自动尝试 8766、8767... 直到 8775，找到可用端口后启动并在该端口打开浏览器

#### 场景: 所有端口被占用
- **当** 8765-8775 全部被占用
- **那么** 进程退出并弹出 OS 原生消息框提示「无可用端口，请释放 8765-8775 范围内端口后重试」

### 需求:仅监听本机
系统必须仅监听 `127.0.0.1`，禁止绑定 `0.0.0.0` 或局域网 IP，避免被同网络其他设备访问。

#### 场景: 外部访问被拒绝
- **当** 同局域网另一台设备尝试访问 `http://<本机IP>:8765`
- **那么** 连接被拒绝，无法访问

### 需求:静态资源托管与 SPA fallback
系统必须通过 FastAPI `StaticFiles` 挂载 `frontend/dist` 目录到根路径。对于非 API 路径（`/api/*`、`/sse/*` 之外的所有路径），必须返回 `index.html` 以支持 Vue Router history 模式。

#### 场景: 访问根路径
- **当** 浏览器请求 `/`
- **那么** 返回 `frontend/dist/index.html`

#### 场景: 访问前端路由
- **当** 浏览器请求 `/mcp/servers`（前端路由）
- **那么** 返回 `index.html`，由 Vue Router 在前端处理路由

#### 场景: 访问 API 路径
- **当** 浏览器请求 `/api/http/send`
- **那么** FastAPI 路由匹配到对应 API，返回 JSON 响应

### 需求:配置目录初始化
系统首次启动时必须检测 `~/.api-tool/` 目录是否存在，不存在则创建并写入空的 `config.json`（结构：`{"version":1,"mcp_servers":[],"llm_providers":[]}`）与空 `history.json`（结构：`{"http_calls":[],"mcp_calls":[],"llm_calls":[]}`）。

#### 场景: 首次启动初始化
- **当** `~/.api-tool/` 不存在
- **那么** 创建目录与默认配置文件，进程继续启动

#### 场景: 配置已存在
- **当** `~/.api-tool/config.json` 已存在
- **那么** 跳过初始化，直接读取现有配置

### 需求:PyInstaller 打包
系统必须通过 PyInstaller 打包为单文件可执行程序。打包入口必须为 `backend/main.py`。打包时必须通过 `--add-data` 把 `frontend/dist` 嵌入 exe。打包产物必须仅依赖系统 Python 标准库 + 嵌入的依赖，目标机器无需安装 Python。

#### 场景: 构建单文件 exe
- **当** 执行 `pyinstaller backend/main.py --onefile --add-data "frontend/dist;frontend/dist"`
- **那么** 在 `dist/` 目录生成 `api-tool.exe`，双击可直接运行

#### 场景: 运行时访问嵌入资源
- **当** exe 启动需要加载 `frontend/dist/index.html`
- **那么** 后端通过 `sys._MEIPASS` 解析资源路径并正确返回

### 需求:开发与生产模式切换
系统必须支持两种运行模式：开发模式（前后端分离，Vite dev server 在 5173，FastAPI 启用 CORS 接受 5173 来源）；生产模式（FastAPI 托管 `frontend/dist`，无 CORS）。模式必须通过环境变量 `APP_ENV` 切换（`development` / `production`）。

#### 场景: 开发模式
- **当** `APP_ENV=development` 启动后端
- **那么** FastAPI 启用 CORSMiddleware 允许 `http://localhost:5173`，前端 Vite dev 服务器代理 `/api` 到后端

#### 场景: 生产模式
- **当** `APP_ENV=production` 启动后端
- **那么** FastAPI 通过 StaticFiles 直接托管 `frontend/dist`，不启用 CORS
