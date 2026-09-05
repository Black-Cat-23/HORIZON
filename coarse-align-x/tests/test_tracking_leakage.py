"""
HORIZON Phase 5 Architectural Integrity & Leakage Tests
==============================================================
Uses Abstract Syntax Tree (AST) static analysis to verify that the
tracking and estimation subsystem contains ZERO references, imports,
or dependencies on ground-truth simulation modules, true target coordinates,
or trajectory generators.
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest

# Modules forbidden from being imported inside tracking/ (except diagnostics/evaluation)
FORBIDDEN_IMPORTS = {
    "simulator.core.simulation",
    "simulator.core.recorder",
    "simulator.trajectories",
    "simulator.world",
    "simulator.camera",
}

FORBIDDEN_SYMBOLS = {
    "TargetState",
    "GroundTruthRecorder",
    "SimulationEngine",
    "VirtualCamera",
    "StraightLineTrajectory",
    "CircularTrajectory",
    "Figure8Trajectory",
    "RandomMotionTrajectory",
}


def test_zero_ground_truth_leakage_in_tracking_engine():
    """Verify via AST parsing that tracking/estimation and tracking/association have zero GT leakage."""
    tracking_dir = Path(__file__).parent.parent / "tracking"
    assert tracking_dir.exists(), f"Tracking directory {tracking_dir} not found"

    core_subdirs = [
        tracking_dir / "estimation",
        tracking_dir / "association",
        tracking_dir / "quality",
    ]

    for subdir in core_subdirs:
        py_files = list(subdir.glob("*.py"))
        assert len(py_files) > 0, f"No python files in {subdir}"

        for py_file in py_files:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))

            for node in ast.walk(tree):
                # 1. Check Import statements
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in FORBIDDEN_IMPORTS:
                            assert not alias.name.startswith(forbidden), (
                                f"Forbidden import '{alias.name}' detected in {py_file.name} (Line {node.lineno})"
                            )

                # 2. Check ImportFrom statements
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for forbidden in FORBIDDEN_IMPORTS:
                        assert not mod.startswith(forbidden), (
                            f"Forbidden import from '{mod}' detected in {py_file.name} (Line {node.lineno})"
                        )
                    for alias in node.names:
                        assert alias.name not in FORBIDDEN_SYMBOLS, (
                            f"Forbidden symbol '{alias.name}' imported in {py_file.name} (Line {node.lineno})"
                        )

                # 3. Check identifier usage
                elif isinstance(node, ast.Name):
                    assert node.id not in FORBIDDEN_SYMBOLS, (
                        f"Forbidden symbol '{node.id}' referenced in {py_file.name} (Line {node.lineno})"
                    )
