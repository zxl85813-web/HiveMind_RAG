Write-Host "Installing .agent/hooks as the Git hooks path..." -ForegroundColor Cyan

if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Host "Git not found." -ForegroundColor Red
    exit 1
}

git config core.hooksPath .agent/hooks

Write-Host "Git Hooks successfully intercepted!" -ForegroundColor Green
Write-Host "The system will now check Conventional Commits and API keys on commit." -ForegroundColor Yellow
Write-Host "Use --no-verify bypass if strictly necessary." -ForegroundColor Gray
