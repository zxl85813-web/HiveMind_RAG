Write-Host "Installing .agent/hooks as the Git hooks path..." -ForegroundColor Cyan

if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Host "Git not found." -ForegroundColor Red
    exit 1
}

git config core.hooksPath .agent/hooks
git config hooks.requireIssueRef true

Write-Host "Git Hooks successfully intercepted!" -ForegroundColor Green
Write-Host "The system will now check Conventional Commits and API keys on commit." -ForegroundColor Yellow
Write-Host "Issue reference check is now STRICT (hooks.requireIssueRef=true)." -ForegroundColor Yellow
Write-Host "Use --no-verify bypass if strictly necessary." -ForegroundColor Gray
