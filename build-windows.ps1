# ============================================================
# api-tool Windows exe 打包脚本（PowerShell）
#
#  在 Windows 上把项目打包为单个可执行文件（PyInstaller onefile）：
#    - 内置 Python 运行时，目标机无需安装 Python
#    - 内置前端 dist（由脚本自动构建），无需安装 Node
#    - 无界面：纯 HTTP 服务，双击启动后浏览器访问
#
#  用法：
#    .\build-windows.ps1                         # 完整打包（构建前端 + 后端）
#    .\build-windows.ps1 -SkipFrontend           # 跳过前端构建（使用已有 frontend/dist）
#    .\build-windows.ps1 -Console                # 生成带控制台窗口的版本（可看日志，适合服务器）
#    .\build-windows.ps1 -Tray                   # 生成带系统托盘的版本（无控制台，右下角托盘图标）
#    .\build-windows.ps1 -SkipNpmCi              # 跳过 npm ci（node_modules 被占用时用，直接复用现有依赖）
#    .\build-windows.ps1 -PythonPath "D:\Program\miniconda3\python.exe"   # 指定 Python 解释器
#    .\build-windows.ps1 -PipIndex https://pypi.tuna.tsinghua.edu.cn/simple   # pip 镜像
#    .\build-windows.ps1 -NoClean                # 保留 PyInstaller 缓存加速二次构建
#
#  产物：backend\dist\api-tool.exe
#
#  运行方式：
#    双击启动（无窗口），浏览器访问 http://localhost:8765
#    自定义端口/数据目录（cmd）：
#      api-tool.exe --port 9000 --data-dir D:\api-tool-data
#    对外服务：
#      api-tool.exe --host 0.0.0.0 --port 8765
#    也可用环境变量 APP_HOST / APP_PORT / APP_CONFIG_DIR（命令行参数优先）
#    托盘版额外参数：--no-tray（临时关闭托盘）--no-open（启动时不自动开浏览器）
# ============================================================
param(
    [switch]$SkipFrontend,
    [switch]$SkipNpmCi,
    [switch]$Console,
    [switch]$Tray,
    [string]$PipIndex = "",
    [string]$PythonPath = "",
    [switch]$NoClean
)

$ErrorActionPreference = "Stop"

# 防止把未知参数（如 --help、拼错的开关）当成"无参数"直接开始打包
if ($args.Count -gt 0) {
    Write-Host ("[错误] 无法识别的参数：" + ($args -join " ")) -ForegroundColor Red
    Write-Host "       可用参数：-SkipFrontend -SkipNpmCi -Console -Tray -NoClean -PipIndex <url> -PythonPath <path>" -ForegroundColor Yellow
    exit 1
}

# ---------- 1. 环境检查 ----------
Write-Host "[1/4] 检查构建环境..." -ForegroundColor Cyan
foreach ($cmd in @("node", "npm")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[错误] 缺少命令: $cmd" -ForegroundColor Red
        exit 1
    }
}

# python 需要真能跑：WindowsApps 里的 python.exe 是商店占位符，执行无输出
if ($PythonPath -ne "") {
    if (-not (Test-Path $PythonPath)) {
        Write-Host "[错误] -PythonPath 指定的解释器不存在：$PythonPath" -ForegroundColor Red
        exit 1
    }
    $pythonExe = (Resolve-Path $PythonPath).Path
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pythonCmd) {
        Write-Host "[错误] 缺少命令: python（可用 -PythonPath 指定解释器）" -ForegroundColor Red
        exit 1
    }
    $pythonExe = $pythonCmd.Source
    if (-not $pythonExe) { $pythonExe = "python" }
}

$pyVersion = (& $pythonExe -c "import sys; print(sys.version.split()[0])" 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $pyVersion -notmatch "^\d+\.\d+") {
    Write-Host "[错误] python 无法正常执行：$pythonExe" -ForegroundColor Red
    Write-Host "       若是 Windows 商店占位符或未安装，请指定真实解释器，例如：" -ForegroundColor Yellow
    Write-Host '         .\build-windows.ps1 -PythonPath "D:\Program\miniconda3\python.exe"' -ForegroundColor Yellow
    exit 1
}
Write-Host ("       python: " + $pyVersion + "  (" + $pythonExe + ")")
Write-Host ("       node:   " + (node --version))

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$venv = Join-Path $root ".venv-win"
$pyInstallerCmd = Join-Path $venv "Scripts\pyinstaller.exe"

# ---------- 2. 构建前端 ----------
if (-not $SkipFrontend) {
    Write-Host "[2/4] 构建前端（npm ci + npm run build）..." -ForegroundColor Cyan
    Set-Location (Join-Path $root "frontend")
    if (-not $SkipNpmCi) {
        & npm ci
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[警告] npm ci 失败。常见原因是 node_modules 里的文件被占用" -ForegroundColor Yellow
            Write-Host "        （vite dev server 的 esbuild 进程、IDE 索引、杀毒软件扫描）。" -ForegroundColor Yellow
            $holders = Get-Process -Name esbuild -ErrorAction SilentlyContinue
            if ($holders) {
                $ids = ($holders | ForEach-Object { $_.Id }) -join ", "
                Write-Host "        检测到正在运行的 esbuild 进程（PID $ids）：若是 npm run dev 请先关掉它。" -ForegroundColor Yellow
            }
            Write-Host "        改用 npm install 增量安装（不会删除 node_modules）..." -ForegroundColor Yellow
            & npm install
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[错误] 前端依赖安装失败。可手动删除 frontend\node_modules 后重试，" -ForegroundColor Red
                Write-Host "        或用 -SkipNpmCi 跳过安装、-SkipFrontend 直接复用已有 dist。" -ForegroundColor Red
                exit 1
            }
            Write-Host "        依赖已通过 npm install 就绪（本次跳过 npm ci 的全量重装）。" -ForegroundColor Green
        }
    } else {
        Write-Host "        跳过依赖安装（-SkipNpmCi），直接使用现有 node_modules。" -ForegroundColor Cyan
    }
    & npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 前端构建失败。" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[2/4] 跳过前端构建（-SkipFrontend）。" -ForegroundColor Cyan
}
if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
    Write-Host "[错误] frontend\dist\index.html 不存在，请先构建前端（或去掉 -SkipFrontend）。" -ForegroundColor Red
    exit 1
}
Write-Host "       前端产物就绪：$root\frontend\dist" -ForegroundColor Green

# ---------- 3. 准备 Python 虚拟环境与依赖 ----------
Write-Host "[3/4] 准备 Python 虚拟环境与打包依赖..." -ForegroundColor Cyan
if (-not (Test-Path $venv)) {
    & $pythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 创建虚拟环境失败：& `"$pythonExe`" -m venv $venv" -ForegroundColor Red
        exit 1
    }
}
$pip = Join-Path $venv "Scripts\pip.exe"
& $pip install --upgrade pip | Out-Null

$pipArgs = @("install")
if ($PipIndex -ne "") { $pipArgs += @("-i", $PipIndex) }
$pipArgs += @(
    "pyinstaller>=6.10.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.7.0",
    "httpx>=0.27.0",
    "mcp>=1.2.0"
)
if ($Tray) {
    # 托盘依赖：pystray 在 Windows 走 ctypes，无需 pywin32；
    # pillow 负责 ico 编码，resvg-py 负责把 frontend/public/favicon.svg 栅格化
    $pipArgs += @("pystray>=0.19.5", "pillow>=10.0.0", "resvg-py>=0.4.0")
    $env:APP_TRAY = "1"
    if ($Console) {
        Write-Host "       -Tray 与 -Console 互斥：托盘版必须无控制台窗口，已忽略 -Console。" -ForegroundColor Yellow
        $Console = $false
    }
}
& $pip @pipArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] pip 依赖安装失败。" -ForegroundColor Red
    exit 1
}

if ($Tray) {
    # 图标生成依赖 pillow，必须放在依赖安装之后
    $py = Join-Path $venv "Scripts\python.exe"
    Write-Host "       生成托盘图标..." -ForegroundColor Cyan
    & $py (Join-Path $root "backend\tray_icon.py") --out (Join-Path $root "backend\build\tray.ico")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 托盘图标生成失败（需要 pillow）。" -ForegroundColor Red
        exit 1
    }
}

# ---------- 4. PyInstaller 打包 ----------
Write-Host "[4/4] PyInstaller 打包（单文件 onefile）..." -ForegroundColor Cyan
$specSrc = Join-Path $root "backend\launcher.spec"

if ($Console) {
    # 生成带控制台窗口的 spec（可看日志，适合服务器部署）
    # 原 spec 为动态判断：console = os.name != "nt"（Windows 无窗口），此处强制 True
    $specWin = Join-Path $root "backend\launcher-windows.spec"
    $content = Get-Content -Raw -Encoding UTF8 $specSrc
    $content = $content.Replace('console = os.name != "nt"', "console = True")
    [System.IO.File]::WriteAllText($specWin, $content, (New-Object System.Text.UTF8Encoding $false))
    $spec = $specWin
} else {
    $spec = $specSrc
}

Set-Location (Join-Path $root "backend")
$pyArgs = @($spec, "--noconfirm")
if (-not $NoClean) { $pyArgs += "--clean" }
& $pyInstallerCmd @pyArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] PyInstaller 打包失败。" -ForegroundColor Red
    exit 1
}

$exe = Join-Path $root "backend\dist\api-tool.exe"
if (-not (Test-Path $exe)) {
    Write-Host "[错误] 未找到产物 $exe，打包失败。" -ForegroundColor Red
    exit 1
}
$size = [math]::Round((Get-Item $exe).Length / 1MB, 1)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
if ($Tray) {
    Write-Host "  打包完成（托盘版）"
    Write-Host "  产物：$exe （${size} MB，单文件可执行程序）" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  运行方式："
    Write-Host "    双击启动 → 右下角托盘出现 ToolDeck 图标，并自动打开浏览器"
    Write-Host "    托盘菜单：打开 ToolDeck / 复制访问地址 / 查看日志 / 退出"
    Write-Host "    临时关闭托盘   api-tool.exe --no-tray"
    Write-Host "    不自动开浏览器 api-tool.exe --no-open"
    Write-Host "    服务日志       %USERPROFILE%\.api-tool\server.log（1 MB × 3 轮转）"
} else {
    Write-Host "  打包完成"
    Write-Host "  产物：$exe （${size} MB，单文件可执行程序）" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  运行方式："
    Write-Host "    双击启动（无窗口），浏览器访问 http://localhost:8765"
    Write-Host "    自定义      api-tool.exe --port 9000 --data-dir D:\api-tool-data"
    Write-Host "    对外服务    api-tool.exe --host 0.0.0.0 --port 8765"
    Write-Host "    后台运行    start /B api-tool.exe --port 8765 > api-tool.log"
    Write-Host ""
    Write-Host "  想要托盘图标版本：.\build-windows.ps1 -Tray"
}
Remove-Item Env:APP_TRAY -ErrorAction SilentlyContinue
Write-Host "  也可用环境变量 APP_HOST / APP_PORT / APP_CONFIG_DIR（命令行参数优先）"
Write-Host "  数据目录默认 %USERPROFILE%\.api-tool（collections.json / history.json / config.json）"
