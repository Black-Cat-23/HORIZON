"""
HORIZON Main Entry Point
================================
CLI interface to execute deterministic simulation experiments headless or
launch the development debug viewer.

Usage:
    # Run 5 seconds headless with figure8 trajectory and export ground truth:
    python main.py --trajectory figure8 --duration 5.0 --export-csv data/ground_truth/run.csv

    # Launch lightweight PySide6 debug viewer:
    python main.py --gui

    # Run custom YAML config:
    python main.py --config configs/default.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from simulator.core.config import (
    AppConfig,
    SimulationConfig,
    TrajectoryConfig,
    load_config,
)
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.presets import get_preset_config


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Path(log_dir) / "simulation.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HORIZON Phase 1 Simulation Engine (SIH26169)"
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--trajectory",
        type=str,
        default=None,
        choices=["straight", "circular", "figure8", "random", "spiral", "sinusoidal"],
        help="Override trajectory type",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Override simulation random seed"
    )
    parser.add_argument(
        "--duration", type=float, default=None, help="Override duration in seconds"
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        choices=["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL", "CUSTOM"],
        help="Disturbance preset (NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL)",
    )
    parser.add_argument(
        "--gui", action="store_true", help="Launch development PySide6 debug viewer"
    )
    parser.add_argument(
        "--export-csv", type=str, default="data/ground_truth/experiment.csv", help="Path to export ground-truth CSV"
    )
    parser.add_argument(
        "--export-json", type=str, default=None, help="Path to export ground-truth JSON"
    )

    args = parser.parse_args()

    # 1. Load config
    if args.config:
        config = load_config(args.config)
    else:
        default_yaml = Path(__file__).parent / "configs" / "default.yaml"
        if default_yaml.exists():
            config = load_config(default_yaml)
        else:
            config = AppConfig()

    # 2. Apply CLI overrides
    if args.trajectory:
        config = AppConfig(
            world=config.world,
            camera=config.camera,
            target=config.target,
            simulation=config.simulation,
            trajectory=TrajectoryConfig(
                type=args.trajectory,
                straight=config.trajectory.straight,
                circular=config.trajectory.circular,
                figure8=config.trajectory.figure8,
                random=config.trajectory.random,
                spiral=config.trajectory.spiral,
                sinusoidal=config.trajectory.sinusoidal,
            ),
            logging=config.logging,
            ground_truth=config.ground_truth,
        )

    if args.seed is not None or args.duration is not None:
        config = AppConfig(
            world=config.world,
            camera=config.camera,
            target=config.target,
            simulation=SimulationConfig(
                frequency_hz=config.simulation.frequency_hz,
                seed=args.seed if args.seed is not None else config.simulation.seed,
                duration_seconds=args.duration if args.duration is not None else config.simulation.duration_seconds,
            ),
            trajectory=config.trajectory,
            logging=config.logging,
            ground_truth=config.ground_truth,
            disturbance=config.disturbance,
        )

    if args.preset is not None:
        dist_cfg = get_preset_config(args.preset)
        config = AppConfig(
            world=config.world,
            camera=config.camera,
            target=config.target,
            simulation=config.simulation,
            trajectory=config.trajectory,
            logging=config.logging,
            ground_truth=config.ground_truth,
            disturbance=dist_cfg,
        )

    # 3. Setup logging
    setup_logging(config.logging.level, config.logging.output_directory)

    # 4. Launch GUI or execute headless simulation
    if args.gui:
        from simulator.visualization.app_shell_view import main as launch_app_shell
        launch_app_shell()
    else:
        engine = SimulationEngine(config)
        engine.initialize()

        total_frames = config.simulation.total_frames
        print(f"Starting headless simulation: {total_frames} frames ({config.simulation.duration_seconds}s @ {config.simulation.frequency_hz}Hz)")
        print(f"Trajectory: {config.trajectory.type} | Seed: {config.simulation.seed}")

        # Progress reporting
        def progress(f, state, frame):
            if f % 60 == 0 or f == total_frames:
                print(f"  Frame {f:4d}/{total_frames} | t={state.timestamp:6.2f}s | pos=({state.x:7.2f}, {state.y:7.2f}) | speed={state.speed:6.2f}px/s")

        engine.run(callback=progress)

        # Export outputs
        if args.export_csv:
            csv_path = engine.recorder.export_csv(args.export_csv)
            print(f"Ground-truth exported to CSV: {csv_path}")

        if args.export_json:
            json_path = engine.recorder.export_json(args.export_json)
            print(f"Ground-truth exported to JSON: {json_path}")

        print("Simulation completed successfully.")


if __name__ == "__main__":
    main()
