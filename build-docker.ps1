# ============================================================
# api-tool 打包 Docker 镜像主脚本（Windows PowerShell）
#
#  镜像运行时只含 Python 环境 + 前端 dist（前端由构建阶段打包进镜像）
#
#  用法：
#    .\build-docker.ps1                       # 构建并启动，镜像 api-tool:latest，端口 8765
#    .\build-docker.ps1 -Export               # 构建 + 导出 ./api-tool.tar（供他人 docker load）+ 启动
#    .\build-docker.ps1 -Export .\dist\api-tool-v1.0.tar -BuildOnly
#                                             # 只构建并导出，不启动
#    .\build-docker.ps1 -Tag api-tool:v1.0 -Port 8080 -DataDir D:\api-tool-data
#
#  他人使用导出的 tar：
#    docker load -i api-tool.tar
#    docker run -d -p 8765:8765 -v apitool-data:/data/api-tool api-tool:latest
# ============================================================
param(
    [string]$Tag = "api-tool:latest",      # 镜像名:标签
    [switch]$Export,                       # 构建后导出 tar 包（默认 ./api-tool.tar）
    [string]$ExportPath = "",              # 自定义导出路径（配合 -Export 使用）
    [switch]$BuildOnly,                    # 只构建（不启动容器）
    [switch]$NoCache,                      # 禁用 Docker 构建缓存
    [int]$Port = 8765,                     # 宿主映射端口
    [string]$DataDir = ""                  # 数据挂载目录（默认命名卷 apitool-data）
)

$ErrorActionPreference = "Stop"

# ---------- 1. 检查 Docker ----------
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未检测到 Docker。请先安装 Docker Desktop：https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    exit 1
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] Docker 服务未启动。请打开 Docker Desktop 并等待其就绪。" -ForegroundColor Red
    exit 1
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# ---------- 2. 构建镜像（多阶段：Node 构建前端 dist -> Python 运行） ----------
$buildArgs = @("build", "-t", $Tag, ".")
if ($NoCache) { $buildArgs += "--no-cache" }
Write-Host "[1/3] 构建镜像 $Tag （前端 dist 将打包进镜像，运行时仅 Python）..." -ForegroundColor Cyan
docker @buildArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 镜像构建失败，请检查上方日志。" -ForegroundColor Red
    exit 1
}
Write-Host "[1/3] 镜像构建完成。" -ForegroundColor Green

# ---------- 3. 导出镜像（可选，用于分发给他人 docker load） ----------
if ($Export) {
    $path = if ($ExportPath -ne "") { $ExportPath } else { Join-Path $root "api-tool.tar" }
    $dir = Split-Path -Parent $path
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Write-Host "[2/3] 导出镜像到 $path ..." -ForegroundColor Cyan
    docker save -o $path $Tag
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 镜像导出失败。" -ForegroundColor Red
        exit 1
    }
    $size = [math]::Round((Get-Item $path).Length / 1MB, 1)
    Write-Host "[2/3] 导出完成（${size} MB）。" -ForegroundColor Green
} else {
    Write-Host "[2/3] 跳过导出（使用 -Export 可生成 tar 镜像包）。" -ForegroundColor DarkGray
}

if ($BuildOnly) {
    Write-Host ""
    Write-Host "[完成] 镜像 $Tag 已就绪。" -ForegroundColor Green
    Write-Host "       导出分发：  docker save -o api-tool.tar $Tag"
    Write-Host "       他人加载：  docker load -i api-tool.tar"
    exit 0
}

# ---------- 4. 启动容器 ----------
Write-Host "[3/3] 启动容器（宿主端口 $Port）..." -ForegroundColor Cyan

# 同名旧容器：先停止删除（数据在卷/挂载目录中，不受影响）
$old = docker ps -a --filter "name=^/api-tool$" --format "{{.Names}}"
if ($old) {
    Write-Host "       检测到旧容器 api-tool，先移除后重建。" -ForegroundColor Yellow
    docker rm -f api-tool | Out-Null
}

$runArgs = @("run", "-d", "--name", "api-tool", "--restart", "unless-stopped", "-p", "${Port}:8765", "-e", "TZ=Asia/Shanghai")
if ($DataDir -ne "") {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    $runArgs += @("-v", "${DataDir}:/data/api-tool")
} else {
    $runArgs += @("-v", "apitool-data:/data/api-tool")
}
$runArgs += $Tag

docker @runArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 容器启动失败。若端口被占用，请用 -Port 指定其他端口。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  部署完成：  http://localhost:$Port" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "常用命令：" -ForegroundColor Yellow
Write-Host "  查看日志     docker logs -f api-tool"
Write-Host "  停止         docker stop api-tool"
Write-Host "  启动         docker start api-tool"
Write-Host "  分发镜像     docker save -o api-tool.tar $Tag"
Write-Host "  他人使用     docker load -i api-tool.tar && docker run -d -p 8765:8765 -v apitool-data:/data/api-tool $Tag"
