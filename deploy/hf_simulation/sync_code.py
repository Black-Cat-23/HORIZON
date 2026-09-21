"""
Project HORIZON — Hugging Face Space Code Synchronizer
======================================================
Safely copies the latest simulation files from coarse-align-x/
into deploy/hf_simulation/ for cloud deployment.
ZERO original files are modified or deleted.
"""

import os
import shutil
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "coarse-align-x"
DEST_DIR = Path(__file__).resolve().parent

# Items to synchronize from coarse-align-x
INCLUDE_DIRS = [
    "configs",
    "control",
    "disturbance",
    "estimation",
    "link_budget",
    "pat",
    "plugins",
    "research",
    "simulator",
    "sources",
    "tracking",
]

INCLUDE_FILES = [
    "main.py",
    "yolov8n.pt",
    "monte_carlo_benchmark_results.json",
]

IGNORE_PATTERNS = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".pytest_cache", "runs", "logs", "*.log"
)

def sync():
    print(f"[Sync] Source directory: {SRC_DIR}")
    print(f"[Sync] Destination directory: {DEST_DIR}")

    if not SRC_DIR.exists():
        raise FileNotFoundError(f"Source directory not found: {SRC_DIR}")

    # 1. Copy essential standalone files
    for fname in INCLUDE_FILES:
        src_file = SRC_DIR / fname
        dest_file = DEST_DIR / fname
        if src_file.exists():
            shutil.copy2(src_file, dest_file)
            print(f"[Sync] Copied file: {fname}")
        else:
            print(f"[Sync] Note: Optional file {fname} not found, skipping.")

    # 2. Copy code directories
    for dname in INCLUDE_DIRS:
        src_subdir = SRC_DIR / dname
        dest_subdir = DEST_DIR / dname
        if src_subdir.exists() and src_subdir.is_dir():
            if dest_subdir.exists():
                shutil.rmtree(dest_subdir)
            shutil.copytree(src_subdir, dest_subdir, ignore=IGNORE_PATTERNS)
            print(f"[Sync] Synced directory: {dname}/")

    print("\n[Sync] Synchronization complete! HF Space package is ready for deployment.")

if __name__ == "__main__":
    sync()
