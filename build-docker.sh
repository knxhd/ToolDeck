#!/usr/bin/env bash
# ============================================================
# api-tool 打包 Docker 镜像主脚本（Linux / macOS / 服务器）
#
#  镜像运行时只含 Python 环境 + 前端 dist（前端由构建阶段打包进镜像）
#
#  用法：
#    ./build-docker.sh                       # 构建并启动，镜像 api-tool:latest，端口 8765
#    ./build-docker.sh --export              # 构建 + 导出 ./api-tool.tar + 启动
#    ./build-docker.sh --tag api-tool:v1.0 --port 8080 --data-dir /srv/api-tool-data
#    ./build-docker.sh --build-only          # 只构建
#
#  他人使用导出的 tar：
#    docker load -i api-tool.tar
#    docker run -d -p 8765:8765 -v apitool-data:/data/api-tool api-tool:latest
# ============================================================
set -e

TAG="api-tool:latest"
EXPORT=""
EXPORT_PATH=""
BUILD_ONLY=""
NO_CACHE=""
PORT=8765
DATA_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag) TAG="$2"; shift 2 ;;
    --export) EXPORT="1"; shift ;;
    --export-path) EXPORT_PATH="$2"; shift 2 ;;
    --build-only) BUILD_ONLY="1"; shift ;;
    --no-cache) NO_CACHE="1"; shift ;;
    --port) PORT="$2"; shift 2 ;;
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# ---------- 1. 检查 Docker ----------
if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未检测到 Docker。请先安装 docker。" >&2
  exit 1
fi
docker info >/dev/null 2>&1 || { echo "[错误] Docker 服务未启动。" >&2; exit 1; }

cd "$(dirname "$0")"

# ---------- 2. 构建镜像 ----------
BUILD_ARGS=(build -t "$TAG" .)
if [[ -n "$NO_CACHE" ]]; then BUILD_ARGS+=(--no-cache); fi
echo "[1/3] 构建镜像 $TAG （前端 dist 将打包进镜像，运行时仅 Python）..."
docker "${BUILD_ARGS[@]}"
echo "[1/3] 镜像构建完成。"

# ---------- 3. 导出镜像（可选） ----------
if [[ -n "$EXPORT" ]]; then
  PATH_OUT="${EXPORT_PATH:-$(pwd)/api-tool.tar}"
  mkdir -p "$(dirname "$PATH_OUT")"
  echo "[2/3] 导出镜像到 $PATH_OUT ..."
  docker save -o "$PATH_OUT" "$TAG"
  SIZE=$(du -h "$PATH_OUT" | cut -f1)
  echo "[2/3] 导出完成（${SIZE}）。"
else
  echo "[2/3] 跳过导出（--export 可生成 tar 镜像包）。"
fi

if [[ -n "$BUILD_ONLY" ]]; then
  echo ""
  echo "[完成] 镜像 $TAG 已就绪。"
  echo "       导出分发：  docker save -o api-tool.tar $TAG"
  echo "       他人加载：  docker load -i api-tool.tar"
  exit 0
fi

# ---------- 4. 启动容器 ----------
echo "[3/3] 启动容器（宿主端口 $PORT）..."
docker rm -f api-tool >/dev/null 2>&1 || true

RUN_ARGS=(run -d --name api-tool --restart unless-stopped -p "${PORT}:8765" -e TZ=Asia/Shanghai)
if [[ -n "$DATA_DIR" ]]; then
  mkdir -p "$DATA_DIR"
  RUN_ARGS+=(-v "${DATA_DIR}:/data/api-tool")
else
  RUN_ARGS+=(-v apitool-data:/data/api-tool)
fi
RUN_ARGS+=("$TAG")

docker "${RUN_ARGS[@]}"

echo ""
echo "============================================================"
echo "  部署完成：  http://localhost:${PORT}"
echo "============================================================"
echo ""
echo "常用命令："
echo "  查看日志     docker logs -f api-tool"
echo "  停止         docker stop api-tool"
echo "  分发镜像     docker save -o api-tool.tar $TAG"
echo "  他人使用     docker load -i api-tool.tar && docker run -d -p 8765:8765 -v apitool-data:/data/api-tool $TAG"
