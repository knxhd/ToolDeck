#!/usr/bin/env bash
# ============================================================
# api-tool Linux 构建镜像并上传到镜像仓库脚本
#
#  用法：
#    ./build-push.sh --registry harbor.example.com/api-tool --tag v1.0 --push --login
#    ./build-push.sh --registry docker.io/yourname/api-tool --tag latest --push
#    ./build-push.sh --registry 10.0.0.8:5000/api-tool --tag v1.0.1 --push
#
#  参数：
#    --registry   镜像仓库地址（含命名空间），如 harbor.example.com/api-tool，必填
#    --tag        版本标签，默认 latest
#    --login      先 docker login（交互输入，或设置 DOCKER_USERNAME / DOCKER_PASSWORD 环境变量免交互）
#    --push       构建后推送到仓库（默认只构建不推送，加 --push 才推送）
#    --no-cache   禁用 Docker 构建缓存
#
#  示例（公司 Harbor 私有仓库）：
#    DOCKER_USERNAME=ci DOCKER_PASSWORD=xxx ./build-push.sh \
#        --registry harbor.example.com/api-tool --tag v1.0 --login --push
#
#  使用方拉取运行：
#    docker pull harbor.example.com/api-tool:v1.0
#    docker run -d --name api-tool -p 8765:8765 \
#        -v apitool-data:/data/api-tool harbor.example.com/api-tool:v1.0
# ============================================================
set -e

REGISTRY=""
TAG="latest"
DO_LOGIN=""
DO_PUSH=""
NO_CACHE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) REGISTRY="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --login) DO_LOGIN="1"; shift ;;
    --push) DO_PUSH="1"; shift ;;
    --no-cache) NO_CACHE="1"; shift ;;
    --help|-h)
      grep -E '^#|^$' "$0" | sed 's/^# \{0,1\}//' | sed -n '1,20p'
      exit 0 ;;
    *) echo "未知参数: $1（--help 查看用法）" >&2; exit 1 ;;
  esac
done

if [[ -z "$REGISTRY" ]]; then
  echo "[错误] 必须指定 --registry，例如 --registry harbor.example.com/api-tool" >&2
  exit 1
fi

# ---------- 0. 检查 Docker ----------
if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未检测到 Docker，请先安装。" >&2
  exit 1
fi
docker info >/dev/null 2>&1 || { echo "[错误] Docker 服务未启动（daemon 不可用）。" >&2; exit 1; }

# ---------- 1. 登录仓库（可选） ----------
if [[ -n "$DO_LOGIN" ]]; then
  # 仓库 host = registry 中第一个 '/' 之前的部分（如 harbor.example.com / docker.io / 10.0.0.8:5000）
  LOGIN_HOST="${REGISTRY%%/*}"
  if [[ -n "$DOCKER_USERNAME" && -n "$DOCKER_PASSWORD" ]]; then
    echo "[1/3] 使用环境变量账号登录 $LOGIN_HOST ..."
    echo "$DOCKER_PASSWORD" | docker login "$LOGIN_HOST" -u "$DOCKER_USERNAME" --password-stdin
  else
    echo "[1/3] 登录 $LOGIN_HOST（交互输入账号密码）..."
    docker login "$LOGIN_HOST"
  fi
else
  echo "[1/3] 跳过登录（如需登录请加 --login）。"
fi

IMAGE="${REGISTRY}:${TAG}"

# ---------- 2. 构建镜像 ----------
BUILD_ARGS=(build -t "$IMAGE" .)
if [[ -n "$NO_CACHE" ]]; then BUILD_ARGS+=(--no-cache); fi
echo "[2/3] 构建镜像 $IMAGE （前端 dist 将打包进镜像，运行时仅 Python）..."
cd "$(dirname "$0")"
docker "${BUILD_ARGS[@]}"
echo "[2/3] 构建完成。"

# ---------- 3. 推送镜像 ----------
if [[ -n "$DO_PUSH" ]]; then
  echo "[3/3] 推送镜像 $IMAGE 到仓库..."
  docker push "$IMAGE"
  echo "[3/3] 推送完成。"
else
  echo "[3/3] 跳过推送（加 --push 上传到仓库）。"
fi

echo ""
echo "============================================================"
echo "  镜像：$IMAGE"
if [[ -n "$DO_PUSH" ]]; then
  echo "  已推送：docker pull $IMAGE"
fi
echo "  本地使用：docker run -d --name api-tool -p 8765:8765 -v apitool-data:/data/api-tool $IMAGE"
echo "============================================================"
