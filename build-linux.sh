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
#    ./build-linux.sh                         # 完整打包（构建前端 + 后端），产物为单文件
#    ./build-linux.sh --skip-frontend         # 跳过前端构建（使用已有 frontend/dist）
#    ./build-linux.sh --pip-index https://pypi.tuna.tsinghua.edu.cn/simple  # 使用镜像源
#    ./build-linux.sh --no-clean              # 保留 PyInstaller 缓存加速二次构建
#
#  产物：backend/dist/api-tool （单文件可执行程序，直接分发运行）
#
#  运行方式（支持自定义端口 / 数据目录 / 监听地址）：
#    # 仅本机访问，默认端口 8765
#    ./api-tool
#    # 自定义端口与数据目录
#    ./api-tool --port 9000 --data-dir /srv/api-tool-data
#    # 服务器上对外提供服务
#    ./api-tool --host 0.0.0.0 --port 8765
#    浏览器访问 http://<服务器IP>:8765
# ============================================================
set -euo pipefail

SKIP_FRONTEND=""
PIP_INDEX=""
CLEAN="--clean"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-frontend) SKIP_FRONTEND="1"; shift ;;
    --pip-index) PIP_INDEX="$2"; shift 2 ;;
    --no-clean) CLEAN=""; shift ;;
    --help|-h)
      grep -E '^#|^$' "$0" | sed 's/^# \{0,1\}//' | sed -n '1,30p'
      exit 0 ;;
    *) echo "未知参数: $1（--help 查看用法）" >&2; exit 1 ;;
  esac
done

cd "$(dirname "$0")"
ROOT="$(pwd)"
VENV="$ROOT/.venv-linux"
PYINSTALLER_CMD="$VENV/bin/pyinstaller"
SPEC_SRC="$ROOT/backend/launcher.spec"
SPEC_LINUX="$ROOT/backend/launcher-linux.spec"

# ---------- 1. 环境检查 ----------
echo "[1/3] 检查构建环境..."
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
  echo "[2/3] 构建前端（npm ci + npm run build）..."
  cd "$ROOT/frontend"
  npm ci
  npm run build
else
  echo "[2/3] 跳过前端构建（--skip-frontend）。"
fi
if [[ ! -f "$ROOT/frontend/dist/index.html" ]]; then
  echo "[错误] frontend/dist/index.html 不存在，请先构建前端（或去掉 --skip-frontend）。" >&2
  exit 1
fi
echo "       前端产物就绪：$ROOT/frontend/dist"

# ---------- 3. 准备 Python 虚拟环境与依赖 ----------
echo "[3/3] 准备 Python 虚拟环境与打包依赖..."
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

# ---------- 4. PyInstaller 打包（onefile，模式由 spec 决定，不传 --onefile/--onedir） ----------
echo "[4/3] PyInstaller 打包（单文件 onefile）..."
# 生成 Linux 专用 spec：控制台输出日志（headless 服务器可观测），其余保持原样
sed 's/console=False,/console=True,/' "$SPEC_SRC" > "$SPEC_LINUX"

cd "$ROOT/backend"
PYARGS=("$SPEC_LINUX" --noconfirm)
if [[ -n "$CLEAN" ]]; then PYARGS+=(--clean); fi
"$PYINSTALLER_CMD" "${PYARGS[@]}"

echo ""
echo "============================================================"
echo "  打包完成"
echo "  产物：$ROOT/backend/dist/api-tool （单文件可执行程序，可直接分发）"
echo ""
echo "  运行方式（支持自定义端口 / 数据目录 / 监听地址）："
echo "    本机访问    ./api-tool"
echo "    自定义      ./api-tool --port 9000 --data-dir /srv/api-tool-data"
echo "    对外服务    ./api-tool --host 0.0.0.0 --port 8765"
echo "    后台运行    nohup ./api-tool --port 8765 > api-tool.log 2>&1 &"
echo ""
echo "  也可用环境变量：APP_HOST / APP_PORT / APP_CONFIG_DIR（命令行参数优先）"
echo "  数据目录默认 ~/.api-tool（collections.json / history.json / config.json）"
echo "============================================================"
