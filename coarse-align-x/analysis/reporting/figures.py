"""
Figure Embedder Module
======================
Image embedding and rendering utilities for report generation.
"""

from __future__ import annotations
from pathlib import Path


class FigureEmbedder:
    """Utilities to embed plot images into HTML and Markdown reports."""

    @staticmethod
    def get_image_markdown(image_path: str, caption: str = "") -> str:
        p = Path(image_path)
        if not p.exists():
            return f"*(Figure {p.name} not found)*"
        return f"![{caption}]({p.as_uri()})"
