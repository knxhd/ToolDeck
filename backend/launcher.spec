"""PyInstaller spec：将 backend + frontend/dist 打包为单一可执行文件。

构建命令：
    cd backend
    pyinstaller launcher.spec --noconfirm --clean

产物：
    dist/api-tool.exe
"""
from pathlib import Path

# spec 文件位于 backend/ 下，项目根目录是其父目录
PROJECT_ROOT = Path(SPECPATH).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ENTRY = PROJECT_ROOT / "backend" / "main.py"

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
    console=False,  # 无控制台窗口（双击直接启动浏览器）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
