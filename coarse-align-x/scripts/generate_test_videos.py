"""
HORIZON Benchmark Video Generator
==================================
Generates 10 challenging synthetic test MP4 videos + companion ground-truth CSVs
for HORIZON PAT system evaluation.

Usage:
    python scripts/generate_test_videos.py

Output (all in data/samples/):
    scenario_01_low_snr.mp4 / _gt.csv
    scenario_02_fast_motion.mp4 / _gt.csv
    scenario_03_occlusion_burst.mp4 / _gt.csv
    scenario_04_distractors.mp4 / _gt.csv
    scenario_05_brightness_ramp.mp4 / _gt.csv
    scenario_06_stop_and_go.mp4 / _gt.csv
    scenario_07_micro_jitter.mp4 / _gt.csv
    scenario_08_multi_segment.mp4 / _gt.csv
    scenario_09_edge_of_fov.mp4 / _gt.csv
    scenario_10_adversarial_combined.mp4 / _gt.csv

DOES NOT modify any HORIZON source file.
"""

from __future__ import annotations
import csv
import math
import random
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import cv2
import numpy as np

# ─── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "samples"
W, H = 640, 480
FPS = 30.0
FOURCC = cv2.VideoWriter_fourcc(*"mp4v")


# ─── Helpers ───────────────────────────────────────────────────────────────────

def gaussian_beacon(frame: np.ndarray, u: float, v: float, sigma: float, peak: float) -> None:
    radius = int(math.ceil(sigma * 4))
    u_i, v_i = int(round(u)), int(round(v))
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            xi = u_i + dx
            yi = v_i + dy
            if 0 <= xi < W and 0 <= yi < H:
                val = peak * math.exp(-0.5 * ((dx ** 2 + dy ** 2) / (sigma ** 2)))
                frame[yi, xi] = min(255, int(frame[yi, xi]) + int(val))


def add_distractor(frame: np.ndarray, u: float, v: float, sigma: float = 3.5, peak: float = 80.0) -> None:
    gaussian_beacon(frame, u, v, sigma, peak)


def flat_bg(noise_sigma: float = 8.0) -> np.ndarray:
    bg = np.random.normal(12.0, noise_sigma, (H, W)).clip(0, 255).astype(np.uint8)
    return bg


def write_video(name: str, frames: List[np.ndarray], gt_rows: List[dict]) -> None:
    mp4_path = OUTPUT_DIR / f"{name}.mp4"
    csv_path = OUTPUT_DIR / f"{name}_gt.csv"
    writer = cv2.VideoWriter(str(mp4_path), FOURCC, FPS, (W, H), isColor=False)
    for f in frames:
        writer.write(f)
    writer.release()
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        fieldnames = ["frame_idx", "timestamp_s", "ground_truth_u", "ground_truth_v", "in_fov"]
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(gt_rows)
    print(f"  OK  {mp4_path.name}  ({len(frames)} frames)  ->  {csv_path.name}")


# ─── Scenarios ─────────────────────────────────────────────────────────────────

def scenario_01_low_snr(n_frames: int = 300) -> None:
    """LOW SNR: beacon barely above noise floor (SNR ~3 dB). Tests HYBRID sensitivity."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    for i in range(n_frames):
        t = i / FPS
        u = cx + 80 * math.sin(2 * math.pi * t / 8.0)
        v = cy + 50 * math.cos(2 * math.pi * t / 6.0)
        bg = flat_bg(noise_sigma=25.0)
        gaussian_beacon(bg, u, v, sigma=5.0, peak=42.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_01_low_snr", frames, gt)


def scenario_02_fast_motion(n_frames: int = 300) -> None:
    """FAST MOTION: ~60 px/s target. Stresses IMM prediction and latency."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    for i in range(n_frames):
        t = i / FPS
        u = cx + (W / 2 - 30) * math.sin(60.0 * math.pi * t / (W / 2))
        v = cy + (H / 2 - 30) * math.cos(60.0 * math.pi * t / (H / 2) * 0.7)
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        bg = flat_bg(noise_sigma=10.0)
        gaussian_beacon(bg, u, v, sigma=4.0, peak=180.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_02_fast_motion", frames, gt)


def scenario_03_occlusion_burst(n_frames: int = 300) -> None:
    """OCCLUSION: 2 blackout bursts (1.3s + 2s). Tests Kalman dead-reckoning and REACQUIRE."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    occlusion_windows = [(80, 120), (190, 250)]
    for i in range(n_frames):
        t = i / FPS
        u = cx + 100 * math.sin(2 * math.pi * t / 10.0)
        v = cy + 60 * math.cos(2 * math.pi * t / 8.0)
        bg = flat_bg(noise_sigma=12.0)
        occluded = any(s <= i <= e for s, e in occlusion_windows)
        if not occluded:
            gaussian_beacon(bg, u, v, sigma=4.5, peak=160.0)
            in_fov = 1
        else:
            cv2.rectangle(bg,
                          (max(0, int(u) - 40), max(0, int(v) - 40)),
                          (min(W - 1, int(u) + 40), min(H - 1, int(v) + 40)),
                          int(np.random.randint(25, 55)), -1)
            in_fov = 0
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": in_fov})
    write_video("scenario_03_occlusion_burst", frames, gt)


def scenario_04_distractors(n_frames: int = 300) -> None:
    """DISTRACTORS: 3 orbiting false targets near the true beacon. Tests association."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    decoys = [(120.0, 0.8, 0.3), (95.0, 1.3, 1.1), (80.0, 0.6, 2.4)]
    for i in range(n_frames):
        t = i / FPS
        u = cx + 70 * math.sin(2 * math.pi * t / 12.0)
        v = cy + 45 * math.cos(2 * math.pi * t / 8.0)
        bg = flat_bg(noise_sigma=10.0)
        for orb_r, spd, phase in decoys:
            du = float(np.clip(cx + orb_r * math.cos(spd * 2 * math.pi * t / 15.0 + phase), 5, W - 5))
            dv = float(np.clip(cy + orb_r * math.sin(spd * 2 * math.pi * t / 12.0 + phase), 5, H - 5))
            add_distractor(bg, du, dv, sigma=3.0, peak=95.0)
        gaussian_beacon(bg, u, v, sigma=5.0, peak=200.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_04_distractors", frames, gt)


def scenario_05_brightness_ramp(n_frames: int = 300) -> None:
    """BRIGHTNESS RAMP: background brightens (solar rise). Tests AGC / SNR robustness."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    for i in range(n_frames):
        t = i / FPS
        u = cx + 90 * math.sin(2 * math.pi * t / 9.0)
        v = cy + 55 * math.cos(2 * math.pi * t / 7.0)
        bg_mean = 8.0 + 52.0 * (i / n_frames)
        bg = flat_bg(noise_sigma=8.0 + 12.0 * (i / n_frames))
        bg = np.clip(bg.astype(np.float32) + bg_mean, 0, 220).astype(np.uint8)
        beacon_peak = 200.0 - 100.0 * (i / n_frames)
        gaussian_beacon(bg, u, v, sigma=5.0, peak=beacon_peak)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_05_brightness_ramp", frames, gt)


def scenario_06_stop_and_go(n_frames: int = 300) -> None:
    """STOP-AND-GO: sudden maneuver impulse. Tests IMM CV->CA->CV model switching."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    u, v, vx, vy = cx, cy, 0.0, 0.0
    for i in range(n_frames):
        t = i / FPS
        dt = 1.0 / FPS
        if 2.0 <= t < 4.0:
            vx += 18.0 * dt; vy += 9.0 * dt
        elif 6.0 <= t < 8.0:
            vx -= 15.0 * dt; vy -= 9.0 * dt
        elif t >= 8.0:
            vx = max(0.0, vx - 5.0 * dt) if vx > 0 else min(0.0, vx + 5.0 * dt)
            vy = max(0.0, vy - 5.0 * dt) if vy > 0 else min(0.0, vy + 5.0 * dt)
        u = float(np.clip(u + vx * dt, 20, W - 20))
        v = float(np.clip(v + vy * dt, 20, H - 20))
        bg = flat_bg(noise_sigma=9.0)
        gaussian_beacon(bg, u, v, sigma=4.5, peak=170.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_06_stop_and_go", frames, gt)


def scenario_07_micro_jitter(n_frames: int = 300) -> None:
    """MICRO-JITTER: high-frequency sub-pixel vibration on slow drift. Tests filter smoothing."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    rng = np.random.default_rng(seed=7)
    for i in range(n_frames):
        t = i / FPS
        u = cx + 50 * math.sin(2 * math.pi * t / 20.0)
        v = cy + 30 * math.cos(2 * math.pi * t / 18.0)
        u += (rng.normal(0, 1.2) + 0.8 * math.sin(2 * math.pi * 15.0 * t) +
              0.4 * math.sin(2 * math.pi * 35.0 * t))
        v += (rng.normal(0, 1.2) + 0.7 * math.cos(2 * math.pi * 22.0 * t) +
              0.3 * math.cos(2 * math.pi * 41.0 * t))
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        bg = flat_bg(noise_sigma=10.0)
        gaussian_beacon(bg, u, v, sigma=3.5, peak=155.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_07_micro_jitter", frames, gt)


def scenario_08_multi_segment(n_frames: int = 450) -> None:
    """MULTI-SEGMENT: Acquire->Track->Lose->Reacquire->Track. Full PAT lifecycle demo."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    for i in range(n_frames):
        t = i / FPS
        if t < 3.0:
            u = 60.0 + (cx - 60) * (t / 3.0); v = 80.0 + (cy - 80) * (t / 3.0)
        elif t < 8.0:
            tau = t - 3.0; u = cx + 110 * math.sin(2 * math.pi * tau / 5.0); v = cy + 70 * math.cos(2 * math.pi * tau / 5.0)
        elif t < 10.0:
            tau = t - 3.0; u = cx + 110 * math.sin(2 * math.pi * tau / 5.0); v = cy + 70 * math.cos(2 * math.pi * tau / 5.0)
        elif t < 13.0:
            tau = t - 10.0; u = cx - 90 + 40 * tau; v = cy - 60 + 25 * tau
        else:
            tau = t - 13.0; u = cx + 60 * math.sin(2 * math.pi * tau / 6.0); v = cy + 40 * math.cos(2 * math.pi * tau / 5.0)
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        occluded = 8.0 <= t < 10.0
        bg = flat_bg(noise_sigma=11.0)
        if not occluded:
            gaussian_beacon(bg, u, v, sigma=5.0, peak=175.0)
            in_fov = 1
        else:
            in_fov = 0
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": in_fov})
    write_video("scenario_08_multi_segment", frames, gt)


def scenario_09_edge_of_fov(n_frames: int = 300) -> None:
    """EDGE-OF-FOV: lemniscate path clips all 4 sensor boundaries. Tests partial PSF detection."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    for i in range(n_frames):
        t = i / FPS
        scale_u, scale_v = W / 2 - 10, H / 2 - 10
        denom = 1 + math.sin(2 * math.pi * t / 8.0) ** 2
        u = cx + scale_u * math.cos(2 * math.pi * t / 8.0) / denom
        v = cy + scale_v * math.sin(2 * math.pi * t / 4.0) * math.cos(2 * math.pi * t / 8.0) / denom
        u_c = float(np.clip(u, 0, W - 1))
        v_c = float(np.clip(v, 0, H - 1))
        in_fov = int(5 <= u <= W - 5 and 5 <= v <= H - 5)
        bg = flat_bg(noise_sigma=10.0)
        if in_fov:
            gaussian_beacon(bg, u_c, v_c, sigma=5.5, peak=165.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": in_fov})
    write_video("scenario_09_edge_of_fov", frames, gt)


def scenario_10_adversarial_combined(n_frames: int = 450) -> None:
    """ADVERSARIAL COMBINED: all failure modes simultaneously — the ISRO evaluator equivalent."""
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    rng = np.random.default_rng(seed=99)
    occlusion_windows = [(150, 185), (300, 330)]
    for i in range(n_frames):
        t = i / FPS
        u = cx + 100 * math.sin(2 * math.pi * t / 7.0) + 40 * math.cos(2 * math.pi * t / 3.1)
        v = cy + 65 * math.cos(2 * math.pi * t / 5.5) + 30 * math.sin(2 * math.pi * t / 2.4)
        u += rng.normal(0, 1.1) + 0.6 * math.sin(2 * math.pi * 18.0 * t)
        v += rng.normal(0, 1.1) + 0.5 * math.cos(2 * math.pi * 25.0 * t)
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        bg_mean = 10.0 + 35.0 * (i / n_frames)
        noise_s = 14.0 + 8.0 * math.sin(2 * math.pi * t / 12.0)
        bg = flat_bg(noise_sigma=noise_s)
        bg = np.clip(bg.astype(np.float32) + bg_mean, 0, 200).astype(np.uint8)
        d1u = float(np.clip(cx + 140 * math.cos(2 * math.pi * t / 9.0), 5, W - 5))
        d1v = float(np.clip(cy + 90 * math.sin(2 * math.pi * t / 7.0), 5, H - 5))
        d2u = float(np.clip(cx - 110 * math.sin(2 * math.pi * t / 6.0 + 1.2), 5, W - 5))
        d2v = float(np.clip(cy - 70 * math.cos(2 * math.pi * t / 8.0 + 0.7), 5, H - 5))
        add_distractor(bg, d1u, d1v, sigma=3.5, peak=88.0)
        add_distractor(bg, d2u, d2v, sigma=3.0, peak=75.0)
        occluded = any(s <= i <= e for s, e in occlusion_windows)
        beacon_peak = max(45.0, 120.0 - 40.0 * (i / n_frames))
        if not occluded:
            gaussian_beacon(bg, u, v, sigma=5.0, peak=beacon_peak)
            in_fov = 1
        else:
            in_fov = 0
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": in_fov})
    write_video("scenario_10_adversarial_combined", frames, gt)


# ─── Hard Trajectory Scenarios ────────────────────────────────────────────────

def scenario_11_sinusoidal_burst(n_frames: int = 360) -> None:
    """
    HIGH-FREQUENCY SINUSOIDAL BURST
    Beacon sweeps left-right at increasing frequency (0.5 Hz → 4 Hz),
    simulating a spacecraft undergoing high-rate angular maneuvers.
    The IMM must continuously switch between CV and CA models as acceleration changes.
    Peak velocity: ~140 px/s at the sinusoid peak.
    """
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    for i in range(n_frames):
        t = i / FPS
        # Chirp: frequency increases linearly from 0.5 → 4.0 Hz
        f_inst = 0.5 + 3.5 * (t / (n_frames / FPS))
        phase = 2 * math.pi * (0.5 * t + 1.75 * t ** 2 / (n_frames / FPS))
        amp_u = W / 2 - 25
        amp_v = H / 2 - 25
        u = cx + amp_u * math.sin(phase)
        v = cy + amp_v * 0.4 * math.sin(phase * 0.618 + 0.7)  # orthogonal wobble
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        bg = flat_bg(noise_sigma=11.0)
        gaussian_beacon(bg, u, v, sigma=4.5, peak=175.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_11_sinusoidal_burst", frames, gt)


def scenario_12_spiral_trajectory(n_frames: int = 360) -> None:
    """
    EXPANDING THEN CONTRACTING SPIRAL
    Radius grows from 10 px → 270 px then collapses back to 10 px.
    Tests Dynamic ROI expansion as target moves away from boresight,
    then contraction during re-centering — a real spacecraft de-tumble scenario.
    """
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    total_t = n_frames / FPS
    max_r = min(cx, cy) - 15
    for i in range(n_frames):
        t = i / FPS
        frac = t / total_t
        # Expand for first half, contract for second half
        r = max_r * (1 - abs(2 * frac - 1))
        angular_speed = 2.5 + 2.0 * frac  # rad/s, speeds up as radius shrinks
        theta = angular_speed * t
        u = cx + r * math.cos(theta)
        v = cy + r * math.sin(theta)
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        bg = flat_bg(noise_sigma=10.0)
        gaussian_beacon(bg, u, v, sigma=5.0, peak=165.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_12_spiral_trajectory", frames, gt)


def scenario_13_lissajous_5_4(n_frames: int = 360) -> None:
    """
    LISSAJOUS FIGURE (5:4 ratio + phase drift)
    The 5:4 frequency ratio produces a quasi-periodic path that never
    exactly repeats within the video. Phase drift (δ sweeping 0→π) means
    the shape continuously morphs — a maximum stress on the IMM predictor
    because consecutive frames are always on a different part of the path.
    """
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    amp_u = W / 2 - 20
    amp_v = H / 2 - 20
    for i in range(n_frames):
        t = i / FPS
        total_t = n_frames / FPS
        delta = math.pi * (t / total_t)  # phase morphs 0 → π
        u = cx + amp_u * math.sin(5 * 2 * math.pi * t / 12.0 + delta)
        v = cy + amp_v * math.sin(4 * 2 * math.pi * t / 12.0)
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        bg = flat_bg(noise_sigma=10.0)
        gaussian_beacon(bg, u, v, sigma=4.5, peak=170.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_13_lissajous_5_4", frames, gt)


def scenario_14_random_walk_jumps(n_frames: int = 360) -> None:
    """
    RANDOM WALK WITH SUDDEN DIRECTION JUMPS
    Gaussian random walk punctuated by 5 sudden velocity reversals.
    Tests REACQUIRE robustness when the filter's prediction completely
    disagrees with the next measurement (high innovation).
    This is the hardest single-source test for the IMM gate logic.
    """
    frames, gt = [], []
    rng = np.random.default_rng(seed=314)
    u, v = float(W / 2), float(H / 2)
    vx, vy = 15.0, 8.0

    # Pre-define jump frames
    jump_frames = {60, 120, 170, 240, 310}

    for i in range(n_frames):
        t = i / FPS
        dt = 1.0 / FPS

        if i in jump_frames:
            # Sudden direction reversal + random magnitude
            angle = rng.uniform(0, 2 * math.pi)
            speed = rng.uniform(30.0, 65.0)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)

        # Random acceleration noise
        vx += rng.normal(0, 2.5)
        vy += rng.normal(0, 2.5)
        # Speed clamp
        spd = math.hypot(vx, vy)
        if spd > 75.0:
            vx *= 75.0 / spd
            vy *= 75.0 / spd

        u = float(np.clip(u + vx * dt, 15, W - 15))
        v = float(np.clip(v + vy * dt, 15, H - 15))
        # Bounce off walls
        if u <= 15 or u >= W - 15:
            vx = -vx
        if v <= 15 or v >= H - 15:
            vy = -vy

        bg = flat_bg(noise_sigma=12.0)
        gaussian_beacon(bg, u, v, sigma=5.0, peak=160.0)
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_14_random_walk_jumps", frames, gt)


def scenario_15_variable_speed_figure8(n_frames: int = 360) -> None:
    """
    VARIABLE-SPEED FIGURE-8 (slow center, fast extremes)
    Standard figure-8 but speed is modulated: the beacon accelerates
    sharply at the crossing point and slows at the tips.
    Physically matches a satellite swinging past opposition in its orbit.
    Max velocity ~120 px/s at the crossover — well above IMM CV threshold.
    Also overlaid with low SNR (peak=90) to compound difficulty.
    """
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    amp_u = W / 2 - 22
    amp_v = H / 2 - 22
    for i in range(n_frames):
        t = i / FPS
        # Standard figure-8 parametric
        theta = 2 * math.pi * t / 10.0
        u_raw = cx + amp_u * math.sin(theta)
        v_raw = cy + amp_v * math.sin(theta) * math.cos(theta)
        # Speed modulation: compress time near centre, expand at tips
        # (warp theta with a sin^3 term)
        warp = 2 * math.pi * t / 10.0 + 0.45 * math.sin(4 * math.pi * t / 10.0)
        u = cx + amp_u * math.sin(warp)
        v = cy + amp_v * math.sin(warp) * math.cos(warp)
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))
        bg = flat_bg(noise_sigma=18.0)  # Low SNR
        gaussian_beacon(bg, u, v, sigma=5.5, peak=90.0)  # Dim beacon
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3), "in_fov": 1})
    write_video("scenario_15_variable_speed_figure8", frames, gt)


def scenario_16_chaotic_superposition(n_frames: int = 450) -> None:
    """
    CHAOTIC MULTI-FREQUENCY SUPERPOSITION
    Five sinusoids with irrational frequency ratios — never repeats.
    Also has 2 occlusion gaps + 3 distractors + brightness ramp.
    This is mathematically the hardest trajectory: the IMM predictor
    cannot fit any polynomial model to the path.

    Frequencies (Hz): 0.13, 0.21, 0.34, 0.55, 0.89  (Fibonacci ratios)
    """
    frames, gt = [], []
    cx, cy = W / 2, H / 2
    rng = np.random.default_rng(seed=271)
    freqs = [0.13, 0.21, 0.34, 0.55, 0.89]  # Fibonacci sequence / 10
    amps_u = [90, 55, 35, 20, 12]
    amps_v = [60, 40, 25, 15, 8]
    occlusion_windows = [(120, 150), (290, 320)]

    for i in range(n_frames):
        t = i / FPS
        u = cx + sum(a * math.sin(2 * math.pi * f * t + 0.3 * k)
                     for k, (f, a) in enumerate(zip(freqs, amps_u)))
        v = cy + sum(a * math.cos(2 * math.pi * f * t + 0.7 * k)
                     for k, (f, a) in enumerate(zip(freqs, amps_v)))
        u = float(np.clip(u, 5, W - 5))
        v = float(np.clip(v, 5, H - 5))

        bg_mean = 10.0 + 40.0 * (i / n_frames)
        bg = flat_bg(noise_sigma=13.0 + 6.0 * math.sin(2 * math.pi * t / 8.0))
        bg = np.clip(bg.astype(np.float32) + bg_mean, 0, 200).astype(np.uint8)

        # 3 distractors
        for j, (df, da, db) in enumerate([(0.17, 130, 0.4), (0.29, 95, 1.8), (0.47, 75, 3.1)]):
            du = float(np.clip(cx + da * math.sin(2 * math.pi * df * t + db), 5, W - 5))
            dv = float(np.clip(cy + da * 0.6 * math.cos(2 * math.pi * df * t + db + 1), 5, H - 5))
            add_distractor(bg, du, dv, sigma=3.0, peak=80.0)

        occluded = any(s <= i <= e for s, e in occlusion_windows)
        beacon_peak = max(50.0, 160.0 - 60.0 * (i / n_frames))
        if not occluded:
            gaussian_beacon(bg, u, v, sigma=5.0, peak=beacon_peak)
            in_fov = 1
        else:
            in_fov = 0
        frames.append(bg)
        gt.append({"frame_idx": i, "timestamp_s": round(t, 4),
                   "ground_truth_u": round(u, 3), "ground_truth_v": round(v, 3),
                   "in_fov": in_fov})
    write_video("scenario_16_chaotic_superposition", frames, gt)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nHORIZON Benchmark Video Generator")
    print(f"Output: {OUTPUT_DIR.resolve()}")
    print("=" * 60)

    scenarios = [
        scenario_01_low_snr,
        scenario_02_fast_motion,
        scenario_03_occlusion_burst,
        scenario_04_distractors,
        scenario_05_brightness_ramp,
        scenario_06_stop_and_go,
        scenario_07_micro_jitter,
        scenario_08_multi_segment,
        scenario_09_edge_of_fov,
        scenario_10_adversarial_combined,
        # ── Hard Trajectory Pack ──
        scenario_11_sinusoidal_burst,
        scenario_12_spiral_trajectory,
        scenario_13_lissajous_5_4,
        scenario_14_random_walk_jumps,
        scenario_15_variable_speed_figure8,
        scenario_16_chaotic_superposition,
    ]

    for fn in scenarios:
        try:
            fn()
        except Exception as exc:
            print(f"  FAIL  {fn.__name__}: {exc}")

    print("=" * 60)
    print(f"Done. {len(scenarios)} test videos generated in data/samples/")
    print()
    print("Evaluation order:")
    print("  WARM-UP  -> 07 jitter, 06 stop-go, 02 fast")
    print("  STANDARD -> 05 brightness, 08 multi-segment, 09 edge-FOV")
    print("  HARD     -> 01 low-SNR, 03 occlusion, 04 distractors")
    print("  FINAL    -> 10 adversarial combined  (ISRO evaluator equivalent)")
    print()
    print("  Hard Trajectory Pack:")
    print("  11 sinusoidal_burst   — chirp 0.5->4 Hz, max 140 px/s")
    print("  12 spiral_trajectory  — expand/contract, speed-up at small radius")
    print("  13 lissajous_5_4      — 5:4 ratio, morphing phase, never repeats")
    print("  14 random_walk_jumps  — 5 sudden direction reversals")
    print("  15 variable_speed_f8  — figure-8, slow center + fast extremes + low SNR")
    print("  16 chaotic_superpos.  — 5 Fibonacci-ratio sinusoids + distractors + occlusion")


if __name__ == "__main__":
    main()
