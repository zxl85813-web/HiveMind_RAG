# 🛡️ [FE-GOV-SYNC]: API 类型同步脚本 (Windows PowerShell 版)
# 职责: 强制同步前后端契约，由后端 Pydantic 模型驱动前端类型生成。

$ErrorActionPreference = "Stop"

$ProjectRoot = Get-Item "$PSScriptRoot\..\.."
$FrontendDir = Get-Item "$PSScriptRoot\.."
$OpenApiJson = "$ProjectRoot\docs\api\openapi.json"
$OutputFile = "$FrontendDir\src\types\api.generated.ts"

# 1. 导出后端 OpenAPI
Write-Host "🏗️ Step 1: Exporting OpenAPI from Backend..." -ForegroundColor Cyan
Set-Location "$ProjectRoot\backend"
python scripts/export_openapi.py

# 2. 生成前端类型
Write-Host "🧬 Step 2: Generating TypeScript types..." -ForegroundColor Cyan
Set-Location $FrontendDir

# 确保 openapi-typescript 可用
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Node.js/npm not found. Please install Node.js."
}

npx openapi-typescript $OpenApiJson --output $OutputFile

Write-Host "✅ Success! API types are now synced at: $OutputFile" -ForegroundColor Green
Write-Host "👉 Use them: import type { components } from '../types/api.generated';" -ForegroundColor Yellow
