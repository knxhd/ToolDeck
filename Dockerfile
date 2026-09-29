# ============================================================
# api-tool 一键 Docker 打包（多阶段构建）
#   阶段1：Node 构建前端 -> frontend/dist
#   阶段2：Python 运行后端（FastAPI 托管静态资源，端口 8765）
# 构建：docker build -t api-tool .
# ============================================================

# ---------- 阶段 1：构建前端 ----------
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# 先装依赖（利用缓存层，package.json/lock 变更才重装）
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com

# 再复制源码并构建
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：运行后端 ----------
FROM python:3.11-slim AS runtime

# 时区与编码
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 后端依赖（版本与 backend/pyproject.toml 保持一致）
COPY backend/pyproject.toml /tmp/backend/
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.7.0" \
    "httpx>=0.27.0" \
    "mcp>=1.2.0"

# 项目代码：backend 源码 + 前端构建产物
WORKDIR /app
COPY backend/ ./backend/
COPY --from=frontend-builder /build/dist/ ./frontend/dist/

# 运行环境
ENV APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8765 \
    APP_CONFIG_DIR=/data/api-tool \
    PYTHONPATH=/app

# 数据卷：集合 / 历史 / 配置持久化（可挂载宿主目录覆盖）
VOLUME ["/data/api-tool"]

EXPOSE 8765

# 健康检查：/api/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=3)"

# 生产入口：uvicorn 直接加载 backend.main:app（绕过本机浏览器/端口探测逻辑）
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8765", "--log-level", "info"]
