Set-Location "$PSScriptRoot"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Staging all files and pushing to GitHub..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

git add -A
git commit -m "fix(build): resolve TypeScript compilation errors for Render static deployment"
git pull --rebase --autostash origin main
git push origin main

Write-Host "`n================================================" -ForegroundColor Green
Write-Host "  Pushed to GitHub successfully! Refresh GitHub." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
