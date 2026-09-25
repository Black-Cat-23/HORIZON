# Hugging Face Space Deployment Guide: HORIZON PySide6 Simulation

This guide explains how to deploy the native Python PySide6 simulation GUI to **Hugging Face Spaces (100% Free Docker Tier)** so it runs interactively in any web browser worldwide.

---

## Step 1: Create your Free Space on Hugging Face (Takes 60 seconds)

1. Go to [Hugging Face](https://huggingface.co/) and log in (create a free account if you don't have one).
2. Click on your profile picture (top right) -> **"New Space"** (or visit: https://huggingface.co/new-space).
3. Fill in the Space details:
   * **Space name**: `horizon-simulation` (or any name you prefer)
   * **License**: `mit` or `apache-2.0`
   * **Space SDK**: Select **Docker** -> Choose **Blank**
   * **Space hardware**: **Free (2 vCPU · 16 GB RAM)**
   * **Visibility**: **Public**
4. Click **"Create Space"**.

---

## Step 2: Push your Simulation to Hugging Face

Open PowerShell in the `deploy/hf_simulation` directory and run:

```powershell
.\deploy_to_hf.ps1
```

* The script will prompt you for your Space Git URL:
  `https://huggingface.co/spaces/YOUR_USERNAME/horizon-simulation`
* When prompted for your password, use your **Hugging Face Access Token** (generated at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) with `Write` permissions).

---

## Step 3: Access your Live Streamed Simulation

Once pushed, Hugging Face will automatically build your Docker container. 
In 2–3 minutes, your live simulation will be online at:

`https://huggingface.co/spaces/YOUR_USERNAME/horizon-simulation`

Or directly via the raw full-screen stream:
`https://YOUR_USERNAME-horizon-simulation.hf.space/`

---

## Step 4: Embedding into your Deployed Landing Page

On your landing page, clicking **"Run Simulation"** can open this exact live stream inside an iframe:

```html
<iframe
  src="https://YOUR_USERNAME-horizon-simulation.hf.space/?autoconnect=true&resize=scale"
  style="width: 100%; height: 100vh; border: none;"
  allow="fullscreen"
></iframe>
```

---

## Future Updates Workflow

Whenever you change any Python file in `coarse-align-x`:
1. Simply run:
   ```powershell
   .\deploy_to_hf.ps1
   ```
2. The script will automatically copy your updated files and push to Hugging Face.
3. Hugging Face reloads your simulation in seconds, with **zero changes needed to your website**!
