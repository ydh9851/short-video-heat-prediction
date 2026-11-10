# ============================================================================
#  build_frontend.ps1  —  前端一键构建（含 Node.js 自举）
#
#  功能：
#    1. 自动检测 Node.js；若本机无 Node，则下载便携版到 .tools/node 并加入 PATH
#    2. 使用淘宝镜像安装依赖
#    3. 执行 npm run build
#    4. 将 dist 同步到后端静态资源目录（target/classes/static/admin 与
#       src/main/resources/static/admin），后端无需重启即可在 /admin 访问
#
#  用法（PowerShell 5，需允许脚本执行）：
#    powershell -ExecutionPolicy Bypass -File build_frontend.ps1
# ============================================================================
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$NODE_PORTABLE_VERSION = "v20.18.1"
$NODE_DIR = Join-Path $root ".tools\node"
$NODE_ZIP = Join-Path $root ".tools\node.zip"
$NPM_REGISTRY = "https://registry.npmmirror.com"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

# ------------------------------------------------------------------ 1. Node
Write-Step "检查 Node.js"
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    Write-Ok "Node $(node --version) 已就绪"
} else {
    Write-Warn "未检测到 Node.js，下载便携版 $NODE_PORTABLE_VERSION 到 $NODE_DIR"
    New-Item -ItemType Directory -Force -Path (Join-Path $root ".tools") | Out-Null
    $url = "https://nodejs.org/dist/$NODE_PORTABLE_VERSION/node-$NODE_PORTABLE_VERSION-win-x64.zip"
    if (-not (Test-Path $NODE_ZIP)) {
        Write-Host "    下载中: $url"
        Invoke-WebRequest -Uri $url -OutFile $NODE_ZIP -UseBasicParsing
    }
    if (Test-Path $NODE_DIR) { Remove-Item $NODE_DIR -Recurse -Force }
    Expand-Archive -Path $NODE_ZIP -DestinationPath (Join-Path $root ".tools") -Force
    $extracted = Get-ChildItem (Join-Path $root ".tools") -Directory | Where-Object { $_.Name -like "node-$NODE_PORTABLE_VERSION-win-x64" } | Select-Object -First 1
    if ($extracted) { Move-Item $extracted.FullName $NODE_DIR -Force }
    $env:PATH = "$NODE_DIR;$env:PATH"
    Write-Ok "Node $(node --version) 已就绪（便携版）"
}

# ------------------------------------------------------------------ 2. 依赖
Write-Step "安装前端依赖"
Set-Location (Join-Path $root "frontend")
if (-not (Test-Path "node_modules")) {
    npm install --registry=$NPM_REGISTRY
} else {
    Write-Ok "node_modules 已存在，跳过 install（如需重装请删除 frontend\node_modules）"
}

# ------------------------------------------------------------------ 3. 构建
Write-Step "执行 npm run build"
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm run build 失败 (exit=$LASTEXITCODE)" }
$dist = Join-Path $root "frontend\dist"
if (-not (Test-Path (Join-Path $dist "index.html"))) { throw "构建产物缺失 index.html" }
Write-Ok "构建完成: $dist"

# ------------------------------------------------------------------ 4. 同步
Write-Step "同步 dist 到后端静态资源"
$targetStatic = Join-Path $root "backend\target\classes\static\admin"
$srcStatic    = Join-Path $root "backend\src\main\resources\static\admin"
foreach ($dest in @($targetStatic, $srcStatic)) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    robocopy $dist $dest /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    # robocopy 返回码 0-7 均为成功
    if ($LASTEXITCODE -gt 7) { throw "robocopy 到 $dest 失败" }
    Write-Ok "已同步: $dest"
}

Set-Location $root
Write-Host "`n================================================" -ForegroundColor Green
Write-Host " 前端构建完成。后端运行时访问 http://localhost:8000/admin" -ForegroundColor Green
Write-Host " 若后端已启动，刷新浏览器即可看到新版本。" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
