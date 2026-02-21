# ═══════════════════════════════════════════════════════
# HiveMind Code Quality — 快速启动脚本
# ═══════════════════════════════════════════════════════
#
# 用法:
#   .\.agent\checks\run_checks.ps1              # 全量检查
#   .\.agent\checks\run_checks.ps1 -Backend     # 仅后端
#   .\.agent\checks\run_checks.ps1 -Frontend    # 仅前端
#   .\.agent\checks\run_checks.ps1 -Report      # 生成 HTML 报告
#   .\.agent\checks\run_checks.ps1 -Fix         # 自动修复
#   .\.agent\checks\run_checks.ps1 -Verbose     # 详细输出
#   .\.agent\checks\run_checks.ps1 -Quick       # 快速检查 (只 lint)
#
# ═══════════════════════════════════════════════════════

param(
    [switch]$Backend,
    [switch]$Frontend,
    [switch]$Report,
    [switch]$Fix,
    [switch]$Verbose,
    [switch]$Quick
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

Write-Host ""
Write-Host "  🐝 HiveMind Code Quality Checker" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

if ($Quick) {
    # 快速模式: 只运行 Ruff + ESLint
    Write-Host "  ⚡ Quick Mode — Lint only" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "  [Backend] Ruff lint..." -ForegroundColor Yellow -NoNewline
    Push-Location "$ProjectRoot\backend"
    $ruffResult = python -m ruff check app/ 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    }
    else {
        Write-Host " ❌" -ForegroundColor Red
        $ruffResult | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }
    Pop-Location
    
    Write-Host "  [Frontend] ESLint..." -ForegroundColor Yellow -NoNewline
    Push-Location "$ProjectRoot\frontend"
    $eslintResult = npx eslint . 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    }
    else {
        Write-Host " ❌" -ForegroundColor Red
        $eslintResult | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }
    Pop-Location
    
    Write-Host ""
    return
}

# 完整检查: 调用 Python 脚本
$args_list = @()
if ($Backend) { $args_list += "--backend" }
if ($Frontend) { $args_list += "--frontend" }
if ($Report) { $args_list += "--report" }
if ($Fix) { $args_list += "--fix" }
if ($Verbose) { $args_list += "--verbose" }

python "$ProjectRoot\.agent\checks\code_quality.py" @args_list
