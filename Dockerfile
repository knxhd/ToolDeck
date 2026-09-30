FROM 10.18.210.112:40080/ai-tenant--aitechcenter-repo/python3:3.10
# 时区与编码
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN groupadd -g 801 hitv \
    && useradd -u 888 -g hitv -d /home/app/ -m -s /bin/bash hitv \
    && mkdir -p /app/backend/ /app/frontend/dist/ /app/logs/

# 后端依赖（版本与 backend/pyproject.toml 保持一致）
COPY backend/pyproject.toml /tmp/backend/
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.7.0" \
    "httpx>=0.27.0" \
    "mcp>=1.2.0"

WORKDIR /app
COPY backend/ /app/backend/
COPY frontend/dist/ /app/frontend/dist/

# 运行环境
ENV APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8765 \
    APP_CONFIG_DIR=/data/api-tool \
    PYTHONPATH=/app

# 数据卷：集合 / 历史 / 配置持久化（可挂载宿主目录覆盖）
VOLUME ["/data/api-tool"]

EXPOSE 8765

LABEL logs.info="python:/app/logs" \
      health.type="http" \
      health.url="http://localhost:8765/api/health"

# 生产入口：uvicorn 直接加载 backend.main:app（绕过本机浏览器/端口探测逻辑）
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8765", "--log-level", "info"]
