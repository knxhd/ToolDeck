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

桌面窗口（仅 Windows）：
    APP_WINDOW=1 pyinstaller launcher.spec
    自动包含托盘，并额外收集 pywebview / pythonnet / WebView2 相关文件，
    在 assets/ 里写入 window.mode 标记；运行时 backend/app/desktop.py 检测到
    该标记才开窗口。Linux / Docker 构建永远不含这些依赖，保持纯 headless。
"""
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# spec 文件位于 backend/ 下，项目根目录是其父目录
PROJECT_ROOT = Path(SPECPATH).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ENTRY = PROJECT_ROOT / "backend" / "main.py"
BUILD_DIR = PROJECT_ROOT / "backend" / "build"

# 构建模式：onefile（默认）/ onedir
APP_BUILD_MODE = os.environ.get("APP_BUILD_MODE", "onefile")
# 桌面窗口（仅 Windows）：内嵌 WebView2 窗口
WINDOW_MODE = os.environ.get("APP_WINDOW", "0") == "1"
# 托盘构建（仅 Windows）：打包 pystray + Pillow + 图标
TRAY_MODE = os.environ.get("APP_TRAY", "0") == "1" or WINDOW_MODE
# 托盘图标（由 build-windows.ps1 调 backend/tray_icon.py 生成）
TRAY_ICON = BUILD_DIR / "tray.ico"
# 窗口版标记文件：作为「本次构建带窗口」的判据
WINDOW_MARKER = BUILD_DIR / "window.mode"
# 无界面 headless 服务：非 Windows 平台保持控制台输出便于观测日志
console = os.name != "nt"
if TRAY_MODE or WINDOW_MODE:
    # 托盘/窗口版必须无控制台窗口（否则双击 exe 会多出一个黑框）
    console = False

datas = []
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
else:
    print(f"[warn] frontend/dist 不存在：{FRONTEND_DIST}，请先执行 `cd frontend && npm run build`")

if WINDOW_MODE:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WINDOW_MARKER.write_text("1", encoding="utf-8")
    datas.append((str(WINDOW_MARKER), "assets"))
    # window.mode 只用于判定（内容无关），存在即代表本次构建带窗口

if TRAY_MODE:
    if TRAY_ICON.exists():
        datas.append((str(TRAY_ICON), "assets"))
    else:
        print(f"[warn] 托盘图标不存在：{TRAY_ICON}，请先执行 `python backend/tray_icon.py`；本次不启用托盘")
        TRAY_MODE = False
        WINDOW_MODE = False

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

if WINDOW_MODE:
    # pywebview 的 GUI 后端（pythonnet / WebView2）全是运行时动态加载，
    # 必须显式收集模块与随包 DLL，否则打包后窗口起不来。
    hiddenimports += [
        "webview",
        "webview.platforms",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "webview.util",
        "clr_loader",
        "pythonnet",
        "clr",
        "bottle",
        "proxy_tools",
    ]
    for package in ("webview", "pythonnet", "clr_loader"):
        try:
            collected_datas, collected_binaries, collected_hidden = collect_all(package)
        except Exception as exc:  # 缺少该包时不要中断打包，只提示
            print(f"[warn] collect_all({package}) 失败：{exc}")
            continue
        datas += collected_datas
        binaries += collected_binaries
        hiddenimports += collected_hidden
    window_excludes = []
else:
    window_excludes = ["webview", "clr", "pythonnet", "clr_loader"]


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
        *window_excludes,
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
