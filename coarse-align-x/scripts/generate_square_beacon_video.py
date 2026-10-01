"""
ISRO SIH26169 High-Fidelity Square Beacon Benchmark Video Generator
===================================================================
Generates a rigorous 30-second (900 frames @ 30 FPS) evaluation video specifically
tailored for ISRO Problem Statement 4 (SIH26169) evaluation.

Specifications adhered to from 26169.pdf:
  - Resolution: 640 x 480 pixels Monochrome FPA
  - Frame Rate: 30.0 Hz
  - Target Shape: STRICTLY SQUARE BEACON (no circular spots)
  - Target Size: 5-20 px dynamic range (7x7 to 18x18 px across phases)
  - Trajectories Covered:
      1. Straight Line (0 - 5s)
      2. Circular Orbit with High Dynamics (5 - 10s)
      3. Sinusoidal Drift with Atmospheric Scintillation (10 - 15s)
      4. Temporary Occlusion / Cloud Eclipse (15 - 18.5s)
      5. Lissajous Figure-of-8 with Severe Camera Jitter (18.5 - 24.5s)
      6. Multi-Disturbance Stress: 10% Salt & Pepper + Rain + Random Maneuvers (24.5 - 30s)
  - Disturbances Covered:
      • Gaussian Noise (sigma up to 18 DN)
      • Poisson Photon Shot Noise
      • Salt & Pepper Noise (10% impulse noise covering entire frame)
      • Camera Jitter (up to +/-18 pixels/frame)
      • Atmospheric Turbulences (contrast fading, optical scintillation, fog attenuation)
      • Dynamic Platform Motion (+/-15 px/frame)

Outputs:
  - data/samples/isro_square_beacon_evaluation_30s.mp4
  - data/samples/isro_square_beacon_evaluation_30s_gt.csv
  - data/samples/isro_square_beacon_evaluation_30s.csv
"""

from __future__ import annotations

import csv
import math
import os
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


def render_subpixel_square_beacon(
    frame: np.ndarray,
    u: float,
    v: float,
    size: float,
    peak_intensity: float,
    blur_sigma: float = 0.0,
) -> None:
    """Render a mathematically exact square beacon with subpixel anti-aliasing.
    
    Guarantees that the photometric Center-of-Gravity matches (u, v) exactly.
    """
    H, W = frame.shape[:2]
    half = size / 2.0
    u_min, u_max = u - half, u + half
    v_min, v_max = v - half, v + half

    i_min = max(0, int(np.floor(u_min)))
    i_max = min(W, int(np.ceil(u_max)) + 1)
    j_min = max(0, int(np.floor(v_min)))
    j_max = min(H, int(np.ceil(v_max)) + 1)

    if i_min >= i_max or j_min >= j_max:
        return

    # Subpixel overlap integration
    sub_patch = np.zeros((j_max - j_min, i_max - i_min), dtype=np.float32)
    for j_idx, y in enumerate(range(j_min, j_max)):
        ov_y = max(0.0, min(y + 0.5, v_max) - max(y - 0.5, v_min))
        if ov_y <= 0:
            continue
        for i_idx, x in enumerate(range(i_min, i_max)):
            ov_x = max(0.0, min(x + 0.5, u_max) - max(x - 0.5, u_min))
            if ov_x <= 0:
                continue
            sub_patch[j_idx, i_idx] = ov_x * ov_y * peak_intensity

    if blur_sigma > 0.3:
        ksize = int(math.ceil(blur_sigma * 3)) * 2 + 1
        sub_patch = cv2.GaussianBlur(sub_patch, (ksize, ksize), blur_sigma)

    target_slice = frame[j_min:j_max, i_min:i_max]
    frame[j_min:j_max, i_min:i_max] = np.clip(target_slice + sub_patch, 0.0, 255.0)


def add_salt_and_pepper_noise(frame: np.ndarray, amount: float = 0.10, salt_vs_pepper: float = 0.5) -> None:
    """Inject 10% Salt & Pepper impulse noise as specified in SIH26169."""
    num_pixels = int(amount * frame.size)
    num_salt = int(num_pixels * salt_vs_pepper)
    num_pepper = num_pixels - num_salt

    H, W = frame.shape[:2]
    # Salt
    ys = np.random.randint(0, H, num_salt)
    xs = np.random.randint(0, W, num_salt)
    frame[ys, xs] = 255.0

    # Pepper
    yp = np.random.randint(0, H, num_pepper)
    xp = np.random.randint(0, W, num_pepper)
    frame[yp, xp] = 0.0


def add_rain_streaks(frame: np.ndarray, num_streaks: int = 40) -> None:
    """Simulate atmospheric optical rain streak disturbances."""
    H, W = frame.shape[:2]
    for _ in range(num_streaks):
        x1 = np.random.randint(0, W)
        y1 = np.random.randint(0, H - 30)
        length = np.random.randint(15, 35)
        angle_rad = math.radians(np.random.uniform(70, 80))
        x2 = int(x1 + length * math.cos(angle_rad))
        y2 = int(y1 + length * math.sin(angle_rad))
        cv2.line(frame, (x1, y1), (x2, y2), 160.0, 1)


def generate_isro_evaluation_video(
    output_video_path: str = "data/samples/isro_square_beacon_evaluation_30s.mp4",
    output_gt_path: str = "data/samples/isro_square_beacon_evaluation_30s_gt.csv",
    width: int = 640,
    height: int = 480,
    fps: float = 30.0,
    duration_s: float = 30.0,
    seed: int = 42,
) -> Tuple[str, str]:
    """Generate the complete 30-second ISRO SIH26169 evaluation benchmark video and ground-truth CSV."""
    np.random.seed(seed)
    total_frames = int(round(fps * duration_s))  # 900 frames
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height), isColor=False)

    gt_rows: List[dict] = []
    dt = 1.0 / fps

    # State variables for trajectories
    cx, cy = width / 2.0, height / 2.0
    u, v = 140.0, 120.0
    vx, vy = 35.0, 22.0

    print(f"Generating ISRO SIH26169 Square Beacon Benchmark Video:")
    print(f"  Target File: {output_video_path}")
    print(f"  Resolution: {width}x{height} Monochrome FPA @ {fps} FPS")
    print(f"  Duration: {duration_s}s ({total_frames} frames)")
    print(f"  Shape: Pure SQUARE Beacon (5-20 px dynamic envelope)")
    print(f"  Phases: Straight Line -> Circular Orbit -> Turbulence/Haze -> Occlusion Eclipse -> Figure-of-8 Jitter -> 10% S&P Stress")

    for f_idx in range(total_frames):
        t = f_idx * dt

        # -------------------------------------------------------------
        # Phase 1: Straight Line & Nominal Acquisition (0.0s - 5.0s, Frames 0 - 149)
        # -------------------------------------------------------------
        if t < 5.0:
            phase_name = "Phase 1: Straight Line & Nominal Acquisition"
            u = 120.0 + 75.0 * t
            v = 110.0 + 48.0 * t
            beacon_size = 10.0  # Default 10x10 px square
            peak_dn = 240.0
            bg_mean = 20.0
            bg_sigma = 8.0
            jitter_u, jitter_v = 0.0, 0.0
            is_occluded = False
            blur_sigma = 0.0
            sp_noise = 0.0
            has_rain = False

        # -------------------------------------------------------------
        # Phase 2: Circular Orbital Trajectory & Platform Vibration (5.0s - 10.0s, Frames 150 - 299)
        # -------------------------------------------------------------
        elif t < 10.0:
            phase_name = "Phase 2: Circular Orbit & Platform Vibration"
            tau = t - 5.0
            omega_circ = 1.15  # ~66 deg/s
            rad_circ = 135.0
            u = cx + rad_circ * math.cos(omega_circ * tau + 0.3)
            v = cy + (rad_circ * 0.75) * math.sin(omega_circ * tau + 0.3)
            # Breathing beacon size: 8x8 to 14x14 px (simulating range expansion)
            beacon_size = 11.0 + 3.0 * math.sin(2.0 * tau)
            peak_dn = 230.0
            bg_mean = 24.0
            bg_sigma = 12.0
            # Platform vibration disturbance
            jitter_u = 4.5 * math.sin(18.0 * tau) + np.random.normal(0, 1.2)
            jitter_v = 4.0 * math.cos(15.0 * tau) + np.random.normal(0, 1.2)
            is_occluded = False
            blur_sigma = 0.0
            sp_noise = 0.0
            has_rain = False

        # -------------------------------------------------------------
        # Phase 3: Atmospheric Turbulence, Haze & Scintillation (10.0s - 15.0s, Frames 300 - 449)
        # -------------------------------------------------------------
        elif t < 15.0:
            phase_name = "Phase 3: Atmospheric Scintillation & Haze"
            tau = t - 10.0
            u = cx + 160.0 * math.sin(0.7 * tau)
            v = cy + 90.0 * math.cos(0.9 * tau)
            beacon_size = 13.0  # 13x13 px
            # Optical scintillation: log-normal intensity fading (flickering between 120 DN and 245 DN)
            scint_factor = math.exp(np.random.normal(0.0, 0.25) - 0.03)
            peak_dn = float(np.clip(210.0 * scint_factor, 115.0, 250.0))
            bg_mean = 35.0  # Atmospheric haze background illumination
            bg_sigma = 15.0
            jitter_u = 2.0 * math.sin(10.0 * tau)
            jitter_v = 2.0 * math.cos(10.0 * tau)
            is_occluded = False
            blur_sigma = 0.8  # Atmospheric turbulence PSF blur
            sp_noise = 0.0
            has_rain = False

        # -------------------------------------------------------------
        # Phase 4: Dense Cloud Eclipse / Full Occlusion (15.0s - 18.5s, Frames 450 - 554)
        # -------------------------------------------------------------
        elif t < 18.5:
            phase_name = "Phase 4: Cloud Eclipse & Re-acquisition"
            tau = t - 15.0
            u = 200.0 + 80.0 * tau
            v = 180.0 + 35.0 * tau
            beacon_size = 10.0
            # Dense cloud occultation between t=16.0s and t=17.0s (30 frames blackout)
            if 16.0 <= t < 17.0:
                is_occluded = True
                peak_dn = 0.0  # Complete blackout
            else:
                is_occluded = False
                # Rapid emergence
                if t < 16.0:
                    fade = max(0.0, 1.0 - (t - 15.6) / 0.4) if t >= 15.6 else 1.0
                else:
                    fade = min(1.0, (t - 17.0) / 0.3)
                peak_dn = 225.0 * fade

            bg_mean = 30.0
            bg_sigma = 10.0
            jitter_u, jitter_v = 0.0, 0.0
            blur_sigma = 0.4 if is_occluded else 0.0
            sp_noise = 0.0
            has_rain = False

        # -------------------------------------------------------------
        # Phase 5: Figure of 8 (Lissajous) with Severe Camera Jitter (18.5s - 24.5s, Frames 555 - 734)
        # -------------------------------------------------------------
        elif t < 24.5:
            phase_name = "Phase 5: Figure-8 with Camera Jitter"
            tau = t - 18.5
            omega_8 = 2.0 * math.pi / 5.5  # 5.5 sec cycle
            u = cx + 190.0 * math.sin(omega_8 * tau)
            v = cy + 120.0 * math.sin(2.0 * omega_8 * tau)
            beacon_size = 12.0
            peak_dn = 235.0
            bg_mean = 22.0
            bg_sigma = 14.0
            # Severe camera platform jitter up to +/-18 pixels/frame
            jitter_u = 12.0 * math.sin(24.0 * tau) + np.random.normal(0, 2.5)
            jitter_v = 9.0 * math.cos(22.0 * tau) + np.random.normal(0, 2.0)
            is_occluded = False
            blur_sigma = 0.0
            sp_noise = 0.0
            has_rain = False

        # -------------------------------------------------------------
        # Phase 6: Multi-Disturbance Stress: 10% Salt & Pepper + Rain + Maneuver (24.5s - 30.0s, Frames 735 - 899)
        # -------------------------------------------------------------
        else:
            phase_name = "Phase 6: 10% Salt & Pepper + Rain Stress"
            tau = t - 24.5
            # Rapid dynamic maneuvering
            u = cx + 140.0 * math.sin(1.4 * tau) + 30.0 * math.cos(3.2 * tau)
            v = cy + 100.0 * math.cos(1.2 * tau) - 25.0 * math.sin(2.8 * tau)
            # Size shifts from 16x16 down to 8x8 px
            beacon_size = 14.0 - 5.0 * (tau / 5.5)
            peak_dn = 240.0
            bg_mean = 25.0
            bg_sigma = 12.0
            jitter_u = 3.0 * math.sin(12.0 * tau)
            jitter_v = 3.0 * math.cos(12.0 * tau)
            is_occluded = False
            blur_sigma = 0.0
            sp_noise = 0.10  # 10% Salt & Pepper noise covering full screen!
            has_rain = True

        # Apply disturbances to actual beacon position on sensor
        actual_u = float(np.clip(u + jitter_u, beacon_size + 2.0, width - beacon_size - 2.0))
        actual_v = float(np.clip(v + jitter_v, beacon_size + 2.0, height - beacon_size - 2.0))

        # Base background with Gaussian noise
        frame_flt = np.random.normal(bg_mean, bg_sigma, (height, width)).astype(np.float32)

        # Render Square Beacon (if not fully occluded)
        if not is_occluded and peak_dn > 5.0:
            render_subpixel_square_beacon(
                frame=frame_flt,
                u=actual_u,
                v=actual_v,
                size=beacon_size,
                peak_intensity=peak_dn,
                blur_sigma=blur_sigma,
            )

        # Poisson shot noise simulation
        poisson_factor = 0.08
        shot_noise = np.random.poisson(np.maximum(0, frame_flt * poisson_factor)) / poisson_factor - frame_flt
        frame_flt = np.clip(frame_flt + shot_noise * 0.35, 0.0, 255.0)

        # Optical rain streaks
        if has_rain:
            add_rain_streaks(frame_flt, num_streaks=35)

        # Salt and Pepper noise (around 10% of image as specified in SIH 26169)
        if sp_noise > 0.0:
            add_salt_and_pepper_noise(frame_flt, amount=sp_noise)

        frame_u8 = np.clip(frame_flt, 0, 255).astype(np.uint8)
        writer.write(frame_u8)

        gt_rows.append({
            "frame_idx": f_idx,
            "timestamp_s": round(t, 4),
            "ground_truth_u": round(actual_u, 3) if not is_occluded else "",
            "ground_truth_v": round(actual_v, 3) if not is_occluded else "",
            "true_u": round(actual_u, 3) if not is_occluded else "",
            "true_v": round(actual_v, 3) if not is_occluded else "",
            "target_size_px": round(beacon_size, 1),
            "target_shape": "SQUARE",
            "phase": phase_name,
            "occluded": 1 if is_occluded else 0,
            "in_fov": 0 if is_occluded else 1,
        })

        if (f_idx + 1) % 150 == 0 or f_idx == total_frames - 1:
            print(f"  Rendered Frame {f_idx + 1:3d}/{total_frames} ({t:5.2f}s) -> {phase_name}")

    writer.release()
    print(f"\n[SUCCESS] Exported Benchmark Video: {output_video_path}")

    # Write reference ground truth CSV files
    fieldnames = [
        "frame_idx",
        "timestamp_s",
        "ground_truth_u",
        "ground_truth_v",
        "true_u",
        "true_v",
        "target_size_px",
        "target_shape",
        "phase",
        "occluded",
        "in_fov",
    ]

    for p in [output_gt_path, output_video_path.replace(".mp4", ".csv")]:
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv_w = csv.DictWriter(f, fieldnames=fieldnames)
            csv_w.writeheader()
            csv_w.writerows(gt_rows)
        print(f"[SUCCESS] Exported Reference Ground Truth: {p}")

    # Also update isro_sample_beacon_30s.mp4 so the GUI default path immediately has the exact square beacon video
    compat_video_path = "data/samples/isro_sample_beacon_30s.mp4"
    compat_gt_path = "data/samples/isro_sample_beacon_30s_gt.csv"
    compat_csv_path = "data/samples/isro_sample_beacon_30s.csv"
    try:
        import shutil
        shutil.copyfile(output_video_path, compat_video_path)
        shutil.copyfile(output_gt_path, compat_gt_path)
        shutil.copyfile(output_gt_path, compat_csv_path)
        print(f"[SUCCESS] Updated GUI default target: {compat_video_path} + GT CSVs")
    except Exception as e:
        print(f"[NOTE] Could not copy to compat path: {e}")

    return output_video_path, output_gt_path


if __name__ == "__main__":
    generate_isro_evaluation_video()
