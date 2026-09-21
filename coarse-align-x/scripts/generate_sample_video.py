"""Generate sample test video for ISRO Performance Evaluation-2.

Creates:
  1. data/samples/isro_sample_beacon_test.mp4 (640x480 @ 30 FPS, 300 frames = 10s)
  2. data/samples/isro_sample_beacon_test_gt.csv (Ground truth pixel coordinates)
"""
import os
import csv
import math
import numpy as np
import cv2

def generate_sample_beacon_video(
    output_video_path: str = "data/samples/isro_sample_beacon_test.mp4",
    output_gt_path: str = "data/samples/isro_sample_beacon_test_gt.csv",
    width: int = 640,
    height: int = 480,
    fps: float = 30.0,
    duration_s: float = 10.0,
    radius: float = 140.0,
    beacon_sigma: float = 4.0,
    noise_sigma: float = 8.0,
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
        omega = 2.0 * math.pi / 5.0  # 1 loop every 5 seconds

        # Target motion: Figure-eight (Lissajous) trajectory
        target_u = center_x + radius * math.sin(omega * t)
        target_v = center_y + (radius * 0.6) * math.sin(2.0 * omega * t)

        # Micro-jitter disturbance
        jitter_u = 2.5 * math.sin(18.0 * t) + np.random.normal(0, 0.5)
        jitter_v = 2.0 * math.cos(15.0 * t) + np.random.normal(0, 0.5)

        actual_u = target_u + jitter_u
        actual_v = target_v + jitter_v

        # Generate Gaussian intensity beacon
        dist_sq = (xx - actual_u) ** 2 + (yy - actual_v) ** 2
        beacon = np.exp(-0.5 * dist_sq / (beacon_sigma ** 2)) * 230.0

        # Background haze & sensor noise
        bg_noise = np.random.normal(25.0, noise_sigma, (height, width))
        frame = np.clip(beacon + bg_noise, 0, 255).astype(np.uint8)

        # Write frame
        out.write(frame)

        gt_rows.append({
            "frame_idx": frame_idx,
            "timestamp_s": round(t, 4),
            "ground_truth_u": round(actual_u, 3),
            "ground_truth_v": round(actual_v, 3),
        })

    out.release()
    print(f"Generated test video: {output_video_path} ({total_frames} frames, {duration_s}s)")

    with open(output_gt_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["frame_idx", "timestamp_s", "ground_truth_u", "ground_truth_v"])
        writer.writeheader()
        writer.writerows(gt_rows)

    print(f"Generated ground truth CSV: {output_gt_path}")

if __name__ == "__main__":
    generate_sample_beacon_video()
