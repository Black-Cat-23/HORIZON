"""
Headless Experiment Runner and Monte Carlo Engine
=================================================
Headless trial runner, batch execution, checkpointing, and parallel trial execution.

Zero GUI Dependency: Pure Python math/numpy execution without PySide6.
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from benchmark.failure import FailureClassifier, FailureCategory
from benchmark.manifest import DeterministicSeedSystem, ExperimentManifest
from benchmark.metrics import MetricEngine
from benchmark.profiles import build_app_config_for_scenario, get_algorithm_profile
from control.camera_controller import PATCameraController
from tracking.estimation.kalman import TargetKalmanFilter
from pat.mode_manager import PATModeManager
from simulator.core.simulation import SimulationEngine
from simulator.perception.config import DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector

logger = logging.getLogger(__name__)


@dataclass
class TrialResult:
    experiment_id: str
    trial_id: str
    algorithm: str
    seed: int
    scenario_id: str
    status: str
    success: bool
    metrics: Dict[str, Any]
    failure_reason: str
    resolved_configuration: Dict[str, Any]
    software_version: str
    timing_summary: Dict[str, float]
    event_summary: Dict[str, int]
    exception_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "trial_id": self.trial_id,
            "algorithm": self.algorithm,
            "seed": self.seed,
            "scenario_id": self.scenario_id,
            "status": self.status,
            "success": self.success,
            "metrics": self.metrics,
            "failure_reason": self.failure_reason,
            "resolved_configuration": self.resolved_configuration,
            "software_version": self.software_version,
            "timing_summary": self.timing_summary,
            "event_summary": self.event_summary,
            "exception_trace": self.exception_trace,
        }

    def save(self, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


def run_single_trial(manifest: ExperimentManifest) -> TrialResult:
    """Execute a single headless simulation trial given an ExperimentManifest."""
    wall_start = time.perf_counter()
    trial_id = f"TRIAL_{manifest.algorithm}_{manifest.scenario_id}_{manifest.trial_seed}"

    # Build AppConfig from manifest resolved parameters
    cfg = build_app_config_for_scenario(
        scenario_id=manifest.scenario_id,
        seed=manifest.trial_seed,
        duration=manifest.simulation_duration,
        frequency=manifest.simulation_frequency,
    )

    try:
        # Initialize Simulation Engine
        engine = SimulationEngine(config=cfg, experiment_id=manifest.experiment_id)
        engine.initialize()

        alg_profile = get_algorithm_profile(manifest.algorithm)

        # Detector Setup
        if manifest.algorithm == "B0":
            detector = None
        elif manifest.algorithm == "B1":
            detector = HybridBeaconDetector(DetectorConfig(perception_mode="CLASSICAL"))
        elif manifest.algorithm == "B2":
            detector = HybridBeaconDetector(DetectorConfig(perception_mode="NEURAL"))
        else:  # OURS
            detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

        # Estimator & PAT Controllers
        estimator = TargetKalmanFilter() if manifest.algorithm != "B0" else None
        pat_mgr = PATModeManager() if manifest.algorithm != "B0" else None
        camera_ctrl = PATCameraController() if manifest.algorithm != "B0" else None

        telemetry_records: List[Dict[str, Any]] = []

        total_frames = cfg.simulation.total_frames
        dt = cfg.simulation.dt

        current_pan = 0.0
        current_tilt = 0.0

        for frame_idx in range(total_frames):
            frame_start = time.perf_counter()
            engine.step()

            gt_state = engine.recorder.records[-1] if engine.recorder.records else None
            true_u = gt_state.target_pixel_u if gt_state else 320.0
            true_v = gt_state.target_pixel_v if gt_state else 240.0

            frame_img = engine.camera.last_observation if engine.camera.last_observation is not None else np.zeros((480, 640), dtype=np.uint8)

            det_x, det_y = None, None
            detected = False
            proc_ms = 0.0

            if detector is not None and frame_img is not None:
                det_res = detector.detect(frame_img, timestamp=engine.clock.current_time)
                proc_ms = det_res.processing_time_ms
                if det_res.detected and det_res.centroid is not None:
                    detected = True
                    det_x, det_y = det_res.centroid

            # Estimation & Control
            est_u, est_v = None, None
            is_sat = False
            state_str = "SEARCH"

            if manifest.algorithm == "B0":
                # Open-loop baseline (no camera movement)
                est_u, est_v = 320.0, 240.0
                state_str = "SEARCH"
            else:
                # Active Closed-Loop PAT
                if estimator is not None:
                    if detected and det_x is not None and det_y is not None:
                        est_res = estimator.update((det_x, det_y), timestamp=engine.clock.current_time)
                        est_u, est_v = est_res.estimated_x, est_res.estimated_y
                    elif estimator.is_initialized:
                        x_pred, _ = estimator.predict(dt=dt)
                        est_u, est_v = float(x_pred[0, 0]), float(x_pred[1, 0])
                    else:
                        est_u, est_v = None, None

                if pat_mgr is not None and camera_ctrl is not None:
                    u_val = est_u if est_u is not None else 320.0
                    v_val = est_v if est_v is not None else 240.0
                    pat_state = pat_mgr.process_step(
                        dt=dt,
                        timestamp_s=engine.clock.current_time,
                        detection_valid=detected,
                        detection_confidence=0.9 if detected else 0.0,
                        mahalanobis_d2=0.5 if detected else 10.0,
                        covariance_trace=5.0,
                        estimated_u_px=u_val,
                        estimated_v_px=v_val,
                        estimated_vx_px_s=0.0,
                        estimated_vy_px_s=0.0,
                        current_pan_deg=current_pan,
                        current_tilt_deg=current_tilt,
                    )
                    state_str = pat_state.mode.name

                    cmd_pan, cmd_tilt, _, _, _, _, is_sat = camera_ctrl.compute_control_command(
                        dt=dt,
                        pat_state=pat_state,
                        search_pan_rate=0.0,
                        search_tilt_rate=0.0,
                        reacquire_pan_rate=0.0,
                        reacquire_tilt_rate=0.0,
                    )
                    current_pan, current_tilt, _, _ = camera_ctrl.actuator_interface.update_actuator(dt)

            frame_proc_time = (time.perf_counter() - frame_start) * 1000.0

            telemetry_records.append({
                "timestamp": engine.clock.current_time,
                "frame_idx": frame_idx,
                "state": state_str,
                "true_x": true_u,
                "true_y": true_v,
                "est_x": est_u,
                "est_y": est_v,
                "det_x": det_x,
                "det_y": det_y,
                "detected": detected,
                "processing_time_ms": max(proc_ms, frame_proc_time),
                "is_saturated": is_sat,
            })

        metric_engine = MetricEngine(
            fov_deg=cfg.camera.fov_horizontal_deg,
            sensor_width_px=cfg.camera.width
        )
        metrics = metric_engine.evaluate_telemetry(telemetry_records)

        classifier = FailureClassifier()
        cat = classifier.classify_trial(metrics)

        wall_duration = time.perf_counter() - wall_start

        return TrialResult(
            experiment_id=manifest.experiment_id,
            trial_id=trial_id,
            algorithm=manifest.algorithm,
            seed=manifest.trial_seed,
            scenario_id=manifest.scenario_id,
            status=cat.value,
            success=cat == FailureCategory.SUCCESS,
            metrics=metrics,
            failure_reason="NONE" if cat == FailureCategory.SUCCESS else cat.value,
            resolved_configuration=manifest.to_dict(),
            software_version=manifest.software_version,
            timing_summary={"sim_time_s": manifest.simulation_duration, "wall_time_s": wall_duration},
            event_summary={
                "target_loss_count": metrics.get("target_loss_count", 0),
                "successful_reacquisition_count": metrics.get("successful_reacquisition_count", 0),
            },
        )

    except Exception as e:
        wall_duration = time.perf_counter() - wall_start
        stack_trace = traceback.format_exc()
        logger.error("Exception in trial execution %s: %s", trial_id, str(e))
        metric_engine = MetricEngine()
        empty_metrics = metric_engine._empty_metrics()
        return TrialResult(
            experiment_id=manifest.experiment_id,
            trial_id=trial_id,
            algorithm=manifest.algorithm,
            seed=manifest.trial_seed,
            scenario_id=manifest.scenario_id,
            status=FailureCategory.RUNTIME_ERROR.value,
            success=False,
            metrics=empty_metrics,
            failure_reason=f"RUNTIME_ERROR: {str(e)}",
            resolved_configuration=manifest.to_dict(),
            software_version=manifest.software_version,
            timing_summary={"sim_time_s": manifest.simulation_duration, "wall_time_s": wall_duration},
            event_summary={},
            exception_trace=stack_trace,
        )


def _worker_run_trial(manifest_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level worker function for multiprocessing execution."""
    manifest = ExperimentManifest.from_dict(manifest_dict)
    res = run_single_trial(manifest)
    return res.to_dict()


class BatchRunner:
    """Batch Monte Carlo experiment runner with checkpointing and optional parallelism."""

    def __init__(self, output_dir: str | Path = "results") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_batch(
        self,
        algorithm: str,
        scenario_id: str,
        master_seed: int = 42,
        trials_count: int = 10,
        seed_start: int = 0,
        duration: float = 10.0,
        parallel: bool = False,
        checkpoint_name: Optional[str] = None,
    ) -> List[TrialResult]:
        """Execute a batch of Monte Carlo trials."""
        alg = algorithm.upper()
        exp_id = f"EXP_{alg}_{scenario_id}_{master_seed}"
        
        checkpoint_dir = self.output_dir / "trials" / exp_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoint_dir / (checkpoint_name or "checkpoint.json")

        completed_results: List[TrialResult] = []
        completed_indices = set()

        # Resume from checkpoint if exists
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    ckpt_data = json.load(f)
                for res_dict in ckpt_data.get("trials", []):
                    res = TrialResult(**res_dict)
                    completed_results.append(res)
                    # Extract trial_index from resolved_configuration
                    t_idx = res.resolved_configuration.get("trial_index", -1)
                    if t_idx >= 0:
                        completed_indices.add(t_idx)
                logger.info("Resumed %d completed trials from checkpoint: %s", len(completed_results), checkpoint_file)
            except Exception as e:
                logger.warning("Could not read checkpoint file %s: %s", checkpoint_file, str(e))

        seed_sys = DeterministicSeedSystem(master_seed=master_seed, scenario_id=scenario_id)

        manifests_to_run = []
        for idx in range(seed_start, seed_start + trials_count):
            if idx in completed_indices:
                continue

            trial_seed = seed_sys.get_trial_seed(idx)
            cfg = build_app_config_for_scenario(scenario_id, seed=trial_seed, duration=duration)

            manifest = ExperimentManifest(
                experiment_id=exp_id,
                algorithm=alg,
                master_seed=master_seed,
                trial_seed=trial_seed,
                trial_index=idx,
                scenario_id=scenario_id,
                simulation_duration=duration,
                simulation_frequency=cfg.simulation.frequency_hz,
                camera_configuration=cfg.camera.__dict__,
                target_configuration=cfg.target.__dict__,
                trajectory_configuration=cfg.trajectory.__dict__,
                disturbance_configuration=cfg.disturbance.__dict__,
                perception_configuration={},
                estimator_configuration={},
                controller_configuration={},
            )
            manifests_to_run.append(manifest)

        if not manifests_to_run:
            return completed_results

        logger.info("Executing %d trials for %s on scenario %s...", len(manifests_to_run), alg, scenario_id)

        if parallel and len(manifests_to_run) > 1:
            num_workers = min(multiprocessing.cpu_count(), len(manifests_to_run))
            logger.info("Running parallel batch across %d worker processes...", num_workers)
            manifest_dicts = [m.to_dict() for m in manifests_to_run]

            with multiprocessing.Pool(processes=num_workers) as pool:
                res_dicts = pool.map(_worker_run_trial, manifest_dicts)

            for rd in res_dicts:
                tr = TrialResult(**rd)
                completed_results.append(tr)
                # Save individual trial output
                tr.save(checkpoint_dir / f"{tr.trial_id}.json")
        else:
            for manifest in manifests_to_run:
                tr = run_single_trial(manifest)
                completed_results.append(tr)
                tr.save(checkpoint_dir / f"{tr.trial_id}.json")

                # Save checkpoint state after each trial
                ckpt_payload = {
                    "experiment_id": exp_id,
                    "count": len(completed_results),
                    "trials": [t.to_dict() for t in completed_results],
                }
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(ckpt_payload, f, indent=2)

        return completed_results
