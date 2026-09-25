import numpy as np
from typing import List, Tuple

def predict_target_positions(state: dict, horizon: int, dt: float, use_acceleration: bool = False) -> List[Tuple[float, float]]:
    """Predict future target angular positions for a horizon of steps.

    Args:
        state: Dictionary containing 'position' (x, y) and 'velocity' (vx, vy).
               If ``use_acceleration`` is True, an ``acceleration`` (ax, ay) entry is expected.
        horizon: Number of future steps to predict.
        dt: Time step between predictions (seconds).
        use_acceleration: Whether to include constant acceleration in the model.

    Returns:
        List of (x, y) tuples for each future step (1-indexed).
    """
    x, y = state["position"]
    vx, vy = state["velocity"]
    ax, ay = (0.0, 0.0)
    if use_acceleration:
        ax, ay = state.get("acceleration", (0.0, 0.0))
    predictions = []
    for i in range(1, horizon + 1):
        t = i * dt
        pred_x = x + vx * t + 0.5 * ax * t * t
        pred_y = y + vy * t + 0.5 * ay * t * t
        predictions.append((pred_x, pred_y))
    return predictions

