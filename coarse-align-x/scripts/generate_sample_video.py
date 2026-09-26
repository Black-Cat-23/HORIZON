"""Generate 30-second sample test video for ISRO Benchmark Performance-2.

Creates:
  1. data/samples/isro_sample_beacon_30s.mp4 (640x480 @ 30 FPS, 900 frames = 30s)
  2. data/samples/isro_sample_beacon_30s_gt.csv (Reference ground truth pixel coordinates)
  3. data/samples/isro_sample_beacon_test.mp4 (10s sample for quick testing)
  4. data/samples/isro_sample_beacon_test_gt.csv
"""
import os
import csv
import math
import numpy as np
import cv2

def generate_sample_beacon_video(
    output_video_path: str = "data/samples/isro_sample_beacon_30s.mp4",
    output_gt_path: str = "data/samples/isro_sample_beacon_30s_gt.csv",
    width: int = 640,
    height: int = 480,
    fps: float = 30.0,
    duration_s: float = 30.0,
    radius: float = 200.0,
    beacon_sigma: float = 4.5,
    noise_sigma: float = 12.0,
) -> None:
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    total_frames = int(fps * duration_s)
    center_x = width / 2.0
    center_y = height / 2.0

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height), isColor=False)

    gt_rows = []
    yy, xx = np.mgrid[0:height, 0:width]

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        omega = 2.0 * math.pi / 7.5  # Full trajectory loop every 7.5 seconds

        # Full-screen moving beacon trajectory (Lissajous figure-8 spanning 400x260 px)
        target_u = center_x + radius * math.sin(omega * t)
        target_v = center_y + (radius * 0.65) * math.sin(2.0 * omega * t)

        # Micro-jitter & atmospheric turbulence disturbance
        jitter_u = 3.0 * math.sin(16.0 * t) + np.random.normal(0, 0.75)
        jitter_v = 2.5 * math.cos(14.0 * t) + np.random.normal(0, 0.75)

        actual_u = float(np.clip(target_u + jitter_u, 15.0, width - 15.0))
        actual_v = float(np.clip(target_v + jitter_v, 15.0, height - 15.0))

        # Cloud fade / temporary fog occultation between t=12s and t=15s (simulating lock loss & reacquisition)
        is_occulted = (12.0 <= t <= 15.0)
        beacon_intensity = 0.0 if is_occulted else 235.0

        # Generate Gaussian intensity spot
        dist_sq = (xx - actual_u) ** 2 + (yy - actual_v) ** 2
        beacon = np.exp(-0.5 * dist_sq / (beacon_sigma ** 2)) * beacon_intensity

        # Add atmospheric noise covering complete screen
        bg_noise = np.random.normal(28.0, noise_sigma, (height, width))
        frame = np.clip(beacon + bg_noise, 0, 255).astype(np.uint8)

        # Write frame
        out.write(frame)

        gt_rows.append({
            "frame_idx": frame_idx,
            "timestamp_s": round(t, 4),
            "ground_truth_u": round(actual_u, 3),
            "ground_truth_v": round(actual_v, 3),
            "occulted": 1 if is_occulted else 0,
        })

    out.release()
    print(f"[OK] Generated test video: {output_video_path} ({total_frames} frames @ {fps:.1f} FPS)")

    with open(output_gt_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["frame_idx", "timestamp_s", "ground_truth_u", "ground_truth_v", "occulted"])
        writer.writeheader()
        writer.writerows(gt_rows)

    print(f"[OK] Generated reference ground truth CSV: {output_gt_path}")

if __name__ == "__main__":
    generate_sample_beacon_video("data/samples/isro_sample_beacon_30s.mp4", "data/samples/isro_sample_beacon_30s_gt.csv", duration_s=30.0)
    generate_sample_beacon_video("data/samples/isro_sample_beacon_test.mp4", "data/samples/isro_sample_beacon_test_gt.csv", duration_s=10.0)
