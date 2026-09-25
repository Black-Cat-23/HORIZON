Set-Location ..
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  HORIZON: Staging and Pushing Changes in 5 Commits" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

Write-Host "`n[1/5] Commit 1: 3D Earth Horizon & Starfield Environment..." -ForegroundColor Yellow
git add website/src/three/components/EarthCurvedHorizon.tsx website/src/three/components/ParticleStarfield.tsx
git commit -m "feat(3d-earth): photorealistic curved daylight Earth horizon and deep space starfield"

Write-Host "`n[2/5] Commit 2: Synchronized Satellite Constellation Relay..." -ForegroundColor Yellow
git add website/src/three/components/RealisticSatellite.tsx
git commit -m "feat(satellites): 5-satellite continuous FOV constellation relay with muted telemetry orbits"

Write-Host "`n[3/5] Commit 3: Flat High-Fidelity Hero Background & Lighting..." -ForegroundColor Yellow
git add website/src/three/ExperienceCanvas.tsx website/src/three/components/HeroBackgroundLayer.tsx website/src/three/components/MilkyWayBackground.tsx
git commit -m "feat(hero-bg): flat uncurved 2D nebula background integration and cinematic orbital lighting"

Write-Host "`n[4/5] Commit 4: Scrollytelling UI, Chapter Flow & Styling..." -ForegroundColor Yellow
git add website/src/App.tsx website/src/chapters/00_PreloadGate.tsx website/src/styles/global.css
git commit -m "feat(ui): seamless scrollytelling transition into Chapter 01 and layout refinement"

Write-Host "`n[5/5] Commit 5: Build Tooling, Asset Pipelines & Verification..." -ForegroundColor Yellow
git add website/vite.config.ts website/public/ .gitignore
git commit -m "chore(build): automated asset pipeline, background streaming, and repository hygiene"

Write-Host "`nPushing all 5 commits to remote origin/main..." -ForegroundColor Green
git push origin main

Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host "  Successfully pushed all 5 commits to GitHub!" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
