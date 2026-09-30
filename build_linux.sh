#!/usr/bin/env bash
# ============================================================
# api-tool Linux 无界面（headless）可运行程序打包脚本
#
#  在 Linux 上把项目打包为单个可执行文件（PyInstaller onefile）：
#    - 内置 Python 运行时，目标机无需安装 Python
#    - 内置前端 dist（由脚本自动构建），无需安装 Node
#    - 无界面：纯 HTTP 服务，通过浏览器/命令行访问
#
#  用法：
#    ./build-linux.sh                         # 完整打包（构建前端 + 后端）并压缩为 tar.gz
#    ./build-linux.sh --skip-frontend         # 跳过前端构建（使用已有 frontend/dist）
#    ./build-linux.sh --tar-name api-tool-1.0.tar.gz   # 自定义压缩包文件名
#    ./build-linux.sh --no-tar                # 不压缩，只生成可执行程序
#    ./build-linux.sh --pip-index https://pypi.tuna.tsinghua.edu.cn/simple  # 使用镜像源
#    ./build-linux.sh --no-clean              # 保留 PyInstaller 缓存加速二次构建
#
#  产物：backend/dist/api-tool （单文件可执行程序）
#  压缩包：api-tool-linux.tar.gz （解压后直接运行，无需安装 Python / Node / GUI）
#
#  无界面运行方式：
#    tar -xzf api-tool-linux.tar.gz
#    # 仅本机访问
#    ./api-tool
#    # 服务器上对外提供服务（允许外部访问）
#    APP_HOST=0.0.0.0 APP_PORT=8765 ./api-tool
#    然后浏览器访问 http://<服务器IP>:8765
# ============================================================
set -euo pipefail

SKIP_FRONTEND=""
PIP_INDEX=""
CLEAN="--clean"
TAR_NAME="api-tool-linux.tar.gz"
NO_TAR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-frontend) SKIP_FRONTEND="1"; shift ;;
    --pip-index) PIP_INDEX="$2"; shift 2 ;;
    --tar-name) TAR_NAME="$2"; shift 2 ;;
    --no-tar) NO_TAR="1"; shift ;;
    --no-clean) CLEAN=""; shift ;;
    --help|-h)
      grep -E '^#|^$' "$0" | sed 's/^# \{0,1\}//' | sed -n '1,28p'
      exit 0 ;;
    *) echo "未知参数: $1（--help 查看用法）" >&2; exit 1 ;;
  esac
done

cd "$(dirname "$0")"
ROOT="$(pwd)"
VENV="$ROOT/.venv-linux"
PYINSTALLER_CMD="$VENV/bin/pyinstaller"
SPEC_SRC="$ROOT/backend/launcher.spec"

# ---------- 1. 环境检查 ----------
echo "[1/4] 检查构建环境..."
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[错误] 本脚本仅支持 Linux（当前: $(uname -s)）。PyInstaller 不能跨平台打包。" >&2
  exit 1
fi
for cmd in python3 node npm; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "[错误] 缺少命令: $cmd（需 python3 / node / npm）" >&2; exit 1; }
done
echo "       python3: $(python3 --version)"
echo "       node:    $(node --version)"

# ---------- 2. 构建前端 ----------
if [[ -z "$SKIP_FRONTEND" ]]; then
  echo "[2/4] 构建前端（npm ci + npm run build）..."
  cd "$ROOT/frontend"
  npm ci
  npm run build
else
  echo "[2/4] 跳过前端构建（--skip-frontend）。"
fi
if [[ ! -f "$ROOT/frontend/dist/index.html" ]]; then
  echo "[错误] frontend/dist/index.html 不存在，请先构建前端（或去掉 --skip-frontend）。" >&2
  exit 1
fi
echo "       前端产物就绪：$ROOT/frontend/dist"

# ---------- 3. 准备 Python 虚拟环境与依赖 ----------
echo "[3/4] 准备 Python 虚拟环境与打包依赖..."
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV" || {
    echo "[提示] venv 创建失败。Ubuntu/Debian 可先安装：sudo apt install python3-venv" >&2
    exit 1
  }
fi
PIP="$VENV/bin/pip"
"$PIP" install --upgrade pip >/dev/null
PIP_ARGS=(install)
if [[ -n "$PIP_INDEX" ]]; then
  PIP_ARGS+=(-i "$PIP_INDEX")
fi
PIP_ARGS+=(
  "pyinstaller>=6.10.0"
  "fastapi>=0.115.0"
  "uvicorn[standard]>=0.30.0"
  "pydantic>=2.7.0"
  "httpx>=0.27.0"
  "mcp>=1.2.0"
)
"$PIP" "${PIP_ARGS[@]}"

# ---------- 4. PyInstaller 打包（onefile） ----------
echo "[4/4] PyInstaller 打包（单文件 onefile）..."
# 给定了 .spec 文件后不能传 --onefile/--onedir，构建模式通过环境变量 APP_BUILD_MODE 在 spec 内指定；
# console 等平台差异也已在 spec 内处理，无需 sed 生成 Linux 专用 spec。
cd "$ROOT/backend"
APP_BUILD_MODE=onefile "$PYINSTALLER_CMD" "$SPEC_SRC" --noconfirm $CLEAN

# ---------- 5. 压缩为 tar.gz（解压即可运行） ----------
if [[ -z "$NO_TAR" ]]; then
  echo "[5/4] 压缩打包为 $TAR_NAME ..."
  tar -czf "$ROOT/$TAR_NAME" -C "$ROOT/backend/dist" api-tool
  TAR_SIZE=$(du -h "$ROOT/$TAR_NAME" | cut -f1)
  echo "[5/4] 压缩完成（${TAR_SIZE}）。"
else
  echo "[5/4] 跳过压缩（--no-tar）。"
fi

echo ""
echo "============================================================"
echo "  打包完成"
echo "  产物：$ROOT/backend/dist/api-tool （单文件）"
if [[ -z "$NO_TAR" ]]; then
  echo "  压缩包：$ROOT/$TAR_NAME （分发此文件即可）"
  echo ""
  echo "  解压使用（目标机无需安装 Python / Node / GUI）："
  echo "    tar -xzf $TAR_NAME"
  echo "    本机访问    ./api-tool"
  echo "    对外服务    APP_HOST=0.0.0.0 APP_PORT=8765 ./api-tool"
  echo "    后台运行    nohup ./api-tool > api-tool.log 2>&1 &"
else
  echo ""
  echo "  运行："
  echo "    本机访问    $ROOT/backend/dist/api-tool"
  echo "    对外服务    APP_HOST=0.0.0.0 APP_PORT=8765 $ROOT/backend/dist/api-tool"
  echo "    后台运行    nohup $ROOT/backend/dist/api-tool > api-tool.log 2>&1 &"
fi
echo ""
echo "  数据目录：~/.api-tool/（可用 APP_CONFIG_DIR 覆盖）"
echo "============================================================"