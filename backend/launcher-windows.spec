"""PyInstaller spec：将 backend + frontend/dist 打包可执行文件。

构建命令：
    cd backend
    pyinstaller launcher.spec --noconfirm --clean

产物：
    dist/api-tool        （onefile 模式，单文件）
    dist/api-tool/       （onedir 模式，目录形式）

模式说明：
    给定了 .spec 文件后，PyInstaller 不允许再传 --onefile/--onedir，
    因此构建模式只能在 spec 内通过环境变量 APP_BUILD_MODE 指定：
        APP_BUILD_MODE=onefile pyinstaller launcher.spec   （默认）
        APP_BUILD_MODE=onedir  pyinstaller launcher.spec
"""
import os
from pathlib import Path

# spec 文件位于 backend/ 下，项目根目录是其父目录
PROJECT_ROOT = Path(SPECPATH).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ENTRY = PROJECT_ROOT / "backend" / "main.py"

# 构建模式：onefile（默认）/ onedir
APP_BUILD_MODE = os.environ.get("APP_BUILD_MODE", "onefile")
# 无界面 headless 服务：非 Windows 平台保持控制台输出便于观测日志
console = True

datas = []
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
else:
    print(f"[warn] frontend/dist 不存在：{FRONTEND_DIST}，请先执行 `cd frontend && npm run build`")

hiddenimports = [
    # uvicorn 相关
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # httpx
    "httpx",
    "httpx._transports",
    "httpx._transports.default",
    # mcp 及其子模块（动态加载）
    "mcp",
    "mcp.client.streamable_http",
    "mcp.client.session",
    "mcp.shared",
    "mcp.shared.exceptions",
    "mcp.types",
    # FastAPI / Starlette / anyio 链路
    "anyio._backends._asyncio",
    "h11",
    "h2",
    "hpack",
    "hyperframe",
    # webbrowser（stdlib，但确保被收集）
    "webbrowser",
    # SSE / StreamingResponse 路径
    "sse_starlette.sse",
]

binaries = []


a = Analysis(
    [str(ENTRY)],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # 排除测试与构建依赖
        "pytest",
        "ruff",
        "mypy",
        "pip",
        "setuptools",
        "wheel",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

if APP_BUILD_MODE == "onedir":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="api-tool",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=console,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="api-tool",
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="api-tool",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=console,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
