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
# Project Root
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Write-Host ""
Write-Host "  🐝 HiveMind Code Quality Checker" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

if ($Quick) {
    Write-Host "  ⚡ Quick Mode — Lint only" -ForegroundColor Yellow
    Write-Host ""
    
    # 后端检查
    Write-Host "  [Backend] Ruff lint..." -ForegroundColor Yellow -NoNewline
    Set-Location "$ProjectRoot\backend"
    python -m ruff check app/
    if ($?) { Write-Host " ✅" -ForegroundColor Green } else { Write-Host " ❌" -ForegroundColor Red }
    
    # 前端检查
    Write-Host "  [Frontend] ESLint..." -ForegroundColor Yellow -NoNewline
    Set-Location "$ProjectRoot\frontend"
    npx eslint .
    if ($?) { Write-Host " ✅" -ForegroundColor Green } else { Write-Host " ❌" -ForegroundColor Red }
    
    Set-Location $ProjectRoot
    Write-Host ""
    exit
}

# 完整检查
$args_list = @()
if ($Backend) { $args_list += "--backend" }
if ($Frontend) { $args_list += "--frontend" }
if ($Report) { $args_list += "--report" }
if ($Fix) { $args_list += "--fix" }
if ($Verbose) { $args_list += "--verbose" }

Set-Location $ProjectRoot
python .agent\checks\code_quality.py $args_list
Write-Host ""
