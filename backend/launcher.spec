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

托盘（仅 Windows）：
    APP_TRAY=1 pyinstaller launcher.spec
    会把 backend/build/tray.ico 打进 assets/ 并收集 pystray + Pillow，
    同时把该图标设为 exe 图标；运行时 backend/app/tray.py 以 assets/tray.ico
    是否存在判断「本次构建带托盘」，非托盘构建则排除 pystray/PIL 以控制体积。
"""
import os
from pathlib import Path

# spec 文件位于 backend/ 下，项目根目录是其父目录
PROJECT_ROOT = Path(SPECPATH).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ENTRY = PROJECT_ROOT / "backend" / "main.py"

# 构建模式：onefile（默认）/ onedir
APP_BUILD_MODE = os.environ.get("APP_BUILD_MODE", "onefile")
# 托盘构建（仅 Windows）：打包 pystray + Pillow + 图标
TRAY_MODE = os.environ.get("APP_TRAY", "0") == "1"
# 托盘图标（由 build-windows.ps1 调 backend/tray_icon.py 生成）
TRAY_ICON = PROJECT_ROOT / "backend" / "build" / "tray.ico"
# 无界面 headless 服务：非 Windows 平台保持控制台输出便于观测日志
console = os.name != "nt"
if TRAY_MODE:
    # 托盘版必须无控制台窗口（否则双击 exe 会多出一个黑框）
    console = False

datas = []
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
else:
    print(f"[warn] frontend/dist 不存在：{FRONTEND_DIST}，请先执行 `cd frontend && npm run build`")

if TRAY_MODE:
    if TRAY_ICON.exists():
        datas.append((str(TRAY_ICON), "assets"))
    else:
        print(f"[warn] 托盘图标不存在：{TRAY_ICON}，请先执行 `python backend/tray_icon.py`；本次不启用托盘")
        TRAY_MODE = False

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
    # Form Data 文件字段：本机原生文件选择对话框（函数内延迟导入）
    "tkinter",
    "tkinter.filedialog",
    # SSE / StreamingResponse 路径
    "sse_starlette.sse",
]

binaries = []

if TRAY_MODE:
    # pystray 的 Windows 后端按需动态导入，必须显式收集
    hiddenimports += [
        "pystray",
        "pystray._win32",
        "pystray._util",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
    ]
    tray_excludes = []
else:
    # 非托盘构建不收集托盘相关依赖（省下 Pillow 的体积）
    tray_excludes = ["pystray", "PIL"]


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
        *tray_excludes,
    ],
    noarchive=False,
)

exe_icon = str(TRAY_ICON) if (TRAY_MODE and TRAY_ICON.exists()) else None

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
        icon=exe_icon,
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
        icon=exe_icon,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
