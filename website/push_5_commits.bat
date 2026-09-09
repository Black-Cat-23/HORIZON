@echo off
cd /d "%~dp0"
if exist ..\.git cd ..

echo =======================================================
echo   HORIZON: Staging All Changes, Rebasing and Pushing
echo =======================================================

echo [1/3] Staging and committing all remaining workspace files...
git add -A
git commit -m "feat(website): complete flat hero background, orbital constellation and scrollytelling enhancements"

echo [2/3] Pulling and rebasing with latest remote commits...
git pull --rebase --autostash origin main

echo [3/3] Pushing all commits to GitHub origin/main...
git push origin main

echo =======================================================
echo   Successfully synchronized and pushed to GitHub!
echo =======================================================
pause
