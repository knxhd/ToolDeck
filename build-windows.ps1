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
# ============================================================
param(
    [switch]$SkipFrontend,
    [switch]$Console,
    [string]$PipIndex = "",
    [switch]$NoClean
)

$ErrorActionPreference = "Stop"

# ---------- 1. 环境检查 ----------
Write-Host "[1/3] 检查构建环境..." -ForegroundColor Cyan
$required = @("python", "node", "npm")
foreach ($cmd in $required) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[错误] 缺少命令: $cmd" -ForegroundColor Red
        exit 1
    }
}
Write-Host ("       python: " + (python --version))
Write-Host ("       node:   " + (node --version))

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$venv = Join-Path $root ".venv-win"
$pyInstallerCmd = Join-Path $venv "Scripts\pyinstaller.exe"

# ---------- 2. 构建前端 ----------
if (-not $SkipFrontend) {
    Write-Host "[2/3] 构建前端（npm ci + npm run build）..." -ForegroundColor Cyan
    Set-Location (Join-Path $root "frontend")
    npm ci
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 前端构建失败。" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[2/3] 跳过前端构建（-SkipFrontend）。" -ForegroundColor Cyan
}
if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
    Write-Host "[错误] frontend\dist\index.html 不存在，请先构建前端（或去掉 -SkipFrontend）。" -ForegroundColor Red
    exit 1
}
Write-Host "       前端产物就绪：$root\frontend\dist" -ForegroundColor Green

# ---------- 3. 准备 Python 虚拟环境与依赖 ----------
Write-Host "[3/3] 准备 Python 虚拟环境与打包依赖..." -ForegroundColor Cyan
if (-not (Test-Path $venv)) {
    python -m venv $venv
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
& $pip @pipArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] pip 依赖安装失败。" -ForegroundColor Red
    exit 1
}

# ---------- 4. PyInstaller 打包 ----------
Write-Host "[4/3] PyInstaller 打包（单文件 onefile）..." -ForegroundColor Cyan
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
Write-Host "  也可用环境变量 APP_HOST / APP_PORT / APP_CONFIG_DIR（命令行参数优先）"
Write-Host "  数据目录默认 %USERPROFILE%\.api-tool（collections.json / history.json / config.json）"
