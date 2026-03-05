# ═══════════════════════════════════════════════════════
# HiveMind Code Quality — 快速启动脚本
# ═══════════════════════════════════════════════════════

param(
    [switch]$Backend,
    [switch]$Frontend,
    [switch]$Report,
    [switch]$Fix,
    [switch]$Verbose,
    [switch]$Quick
)

$ErrorActionPreference = "Stop"
# 获取脚本所在目录的根目录 (project root)
$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $CurrentDir)

Write-Host ""
Write-Host "  🐝 HiveMind Code Quality Checker" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

if ($Quick) {
    Write-Host "  ⚡ Quick Mode — Lint only" -ForegroundColor Yellow
    Write-Host ""
    
    # 后端检查
    Write-Host "  [Backend] Ruff lint..." -ForegroundColor Yellow -NoNewline
    $BackendDir = Join-Path $ProjectRoot "backend"
    Push-Location $BackendDir
    try {
        $ruffResult = python -m ruff check app/ 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅" -ForegroundColor Green
        }
        else {
            Write-Host " ❌" -ForegroundColor Red
            $ruffResult | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        }
    }
    finally {
        Pop-Location
    }
    
    # 前端检查
    Write-Host "  [Frontend] ESLint..." -ForegroundColor Yellow -NoNewline
    $FrontendDir = Join-Path $ProjectRoot "frontend"
    Push-Location $FrontendDir
    try {
        $eslintResult = npx eslint . 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅" -ForegroundColor Green
        }
        else {
            Write-Host " ❌" -ForegroundColor Red
            $eslintResult | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host ""
}
else {
    # 完整检查: 调用 Python 脚本
    $args_list = @()
    if ($Backend) { $args_list += "--backend" }
    if ($Frontend) { $args_list += "--frontend" }
    if ($Report) { $args_list += "--report" }
    if ($Fix) { $args_list += "--fix" }
    if ($Verbose) { $args_list += "--verbose" }

    $CheckScript = Join-Path $ProjectRoot ".agent\checks\code_quality.py"
    python $CheckScript @args_list
}
