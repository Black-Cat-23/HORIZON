# Project HORIZON — Hugging Face Space One-Click Deployment Script
# ====================================================================

param (
    [string]$SpaceRepoUrl = ""
)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  HORIZON: Deploy PySide6 Simulation to Hugging Face Spaces     " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Run Synchronizer
Write-Host "[1/3] Synchronizing latest simulation code from coarse-align-x..." -ForegroundColor Yellow
python sync_code.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Error] Code synchronization failed." -ForegroundColor Red
    exit 1
}

# 2. Check Git Repo URL
if (-not $SpaceRepoUrl) {
    Write-Host ""
    Write-Host "Please enter your Hugging Face Space Git URL:" -ForegroundColor Green
    Write-Host "(Example: https://huggingface.co/spaces/YOUR_USERNAME/horizon-simulation)" -ForegroundColor Gray
    $SpaceRepoUrl = Read-Host "HF Space Git URL"
}

if (-not $SpaceRepoUrl) {
    Write-Host "[Error] Space Git URL is required." -ForegroundColor Red
    exit 1
}

# 3. Git Operations
Write-Host ""
Write-Host "[2/3] Preparing deployment repository..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

# Set remote 'hf'
$existingRemote = git remote | Where-Object { $_ -eq "hf" }
if ($existingRemote) {
    git remote set-url hf $SpaceRepoUrl
} else {
    git remote add hf $SpaceRepoUrl
}

Write-Host "[3/3] Committing and pushing to Hugging Face Spaces..." -ForegroundColor Yellow
git add -A
git commit -m "Deploy HORIZON PySide6 simulation suite to Hugging Face Space"

Write-Host "Pushing to Hugging Face (you may be prompted for your HF Token/Password)..." -ForegroundColor Cyan
git push -u hf main --force

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "  SUCCESS! Deployment pushed to Hugging Face Spaces!             " -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "Hugging Face is now building your Docker container." -ForegroundColor Cyan
    Write-Host "Once build completes, your live simulation will be available at:" -ForegroundColor Cyan
    Write-Host "$SpaceRepoUrl" -ForegroundColor White
} else {
    Write-Host "[Error] Git push failed. Please verify your Hugging Face credentials/token." -ForegroundColor Red
}
