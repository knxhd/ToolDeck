# api-tool Docker 镜像打包与分发

整个项目（Vue3 前端 + FastAPI 后端）打包成一个 Docker 镜像：**运行时镜像只依赖 Python 环境**，前端在构建阶段编译为 `dist` 直接打进镜像，由后端托管，访问方式与本地完全一致。

## 前置条件

- 安装 Docker（Windows 用 Docker Desktop，Linux/macOS 用 docker）
- **构建**时需要联网（`npm ci` 拉前端依赖、`pip install` 拉后端依赖）；**运行**镜像不需要联网

## 文件清单

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 多阶段构建：阶段1 Node 构建前端 dist → 阶段2 Python 运行镜像（只含 Python + dist） |
| `build-push.sh` | **Linux 构建 + 上传镜像仓库脚本**（Harbor / Docker Hub / 私有 registry） |
| `build-docker.ps1` | Windows 主脚本：构建镜像 + 可选导出 tar + 启动容器 |
| `build-docker.sh` | Linux/macOS 主脚本：构建 + 可选导出 tar + 启动容器 |
| `docker-compose.yml` | 备选编排（compose 一键构建启动） |
| `.dockerignore` | 排除 node_modules / dist / 缓存，控制镜像体积 |

## 〇、Linux 构建镜像并上传仓库（发布流程）

在 Linux 上构建镜像并推到私有镜像库（Harbor / Nexus / Docker Hub / 阿里云 ACR 等）：

```bash
cd /path/to/api-tool
chmod +x build-push.sh

# 构建 + 登录 + 推送（Harbor 示例，交互输入账号密码）
./build-push.sh --registry harbor.example.com/api-tool --tag v1.0 --login --push

# 免交互（CI 或脚本中）
DOCKER_USERNAME=ci DOCKER_PASSWORD=xxx \
  ./build-push.sh --registry harbor.example.com/api-tool --tag v1.0 --login --push

# 只构建不推送
./build-push.sh --registry harbor.example.com/api-tool --tag v1.0

# 自定义端口 registry（如内网 10.0.0.8:5000）
./build-push.sh --registry 10.0.0.8:5000/api-tool --tag v1.0.1 --push
```

对方拉取使用：

```bash
docker pull harbor.example.com/api-tool:v1.0
docker run -d --name api-tool -p 8765:8765 -v apitool-data:/data/api-tool harbor.example.com/api-tool:v1.0
```

> Docker Hub 方式：`--registry docker.io/你的用户名/api-tool --tag latest --login --push`

## 一、Windows：一键构建并启动

```powershell
cd E:\coding\api-tool
.\build-docker.ps1          # 构建镜像 + 启动容器，访问 http://localhost:8765
```

常用参数：

```powershell
.\build-docker.ps1 -Export                     # 额外导出 ./api-tool.tar 供他人使用
.\build-docker.ps1 -Export .\dist\api-tool-v1.0.tar -BuildOnly   # 只构建+导出，不启动
.\build-docker.ps1 -Tag api-tool:v1.0          # 自定义镜像标签
.\build-docker.ps1 -Port 8080                  # 宿主端口改为 8080
.\build-docker.ps1 -DataDir D:\api-tool-data   # 数据挂载到指定目录
.\build-docker.ps1 -NoCache                    # 禁用缓存重建
```

## 二、Linux / macOS / 服务器：一键构建并启动

```bash
chmod +x build-docker.sh
./build-docker.sh                     # 构建 + 启动
./build-docker.sh --export            # 构建 + 导出 tar + 启动
./build-docker.sh --tag api-tool:v1.0 --port 8080 --data-dir /srv/api-tool-data
./build-docker.sh --build-only        # 只构建
```

## 三、手动构建

```bash
docker build -t api-tool .
docker run -d --name api-tool -p 8765:8765 -v apitool-data:/data/api-tool api-tool
```

## 四、分发给他人使用（核心流程）

把镜像导出为 tar 文件，对方 `docker load` 后即可运行，无需源码、无需 Node：

**打包方（你已经构建好镜像）：**

```powershell
docker save -o api-tool.tar api-tool:latest
# 把 api-tool.tar 发给对方（U盘 / 网盘 / scp 均可）
```

**使用方（任何装有 Docker 的机器）：**

```bash
docker load -i api-tool.tar
docker run -d --name api-tool -p 8765:8765 -v apitool-data:/data/api-tool api-tool:latest
```

然后浏览器打开 `http://localhost:8765` 即可使用。数据（集合/历史/配置）保存在命名卷 `apitool-data`，删容器不丢数据。

> 若对方在公网服务器，可先 `docker load` 后改用 compose：`docker compose up -d`（文件在仓库 `docker-compose.yml`）。

## 数据持久化

- 集合 / 历史 / 配置保存在容器内 `/data/api-tool`（后端 `APP_CONFIG_DIR`）
- 默认使用 Docker 命名卷 `apitool-data`；也可挂载宿主目录：`-v D:\api-tool-data:/data/api-tool`

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `APP_PORT` | `8765` | 后端端口（容器内固定，宿主端口由 `-p` 控制） |
| `APP_CONFIG_DIR` | `/data/api-tool` | 数据目录（建议保持挂载卷路径） |
| `APP_ENV` | `production` | 生产模式托管前端静态资源 |
| `TZ` | `Asia/Shanghai` | 时区 |

## 常见问题

- **端口被占用**：`docker run -p 8080:8765 ...` 或脚本 `-Port 8080`
- **构建时 npm 慢/失败**：`Dockerfile` 中 `npm ci` 已指定 npmmirror 镜像源
- **对方加载镜像提示空间不足**：`docker system prune` 清理后重试
- **镜像体积较大（约数百 MB）**：主要来自 Python 运行环境与 Monaco 编辑器静态资源，属正常
