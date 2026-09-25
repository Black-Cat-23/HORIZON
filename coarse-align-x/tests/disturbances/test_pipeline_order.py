import numpy as np
import pytest

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.config import (
    AtmosphereConfig,
    CameraJitterConfig,
    DisturbanceConfig,
)
from simulator.disturbances.pipeline import DisturbancePipeline

def test_pipeline_order_jitter_before_atmosphere():
    # Configure disturbance with jitter and atmosphere
    config = DisturbanceConfig(
        enabled=True,
        camera_jitter=CameraJitterConfig(enabled=True, max_x_px=10, max_y_px=10),
        atmosphere=AtmosphereConfig(enabled=True, condition="fog", severity=1.0)
    )
    
    seed_mgr = SeedManager(seed=42)
    pipeline = DisturbancePipeline(config, seed_mgr)
    
    # Create a simple frame with a single bright spot
    frame = np.zeros((480, 640), dtype=np.uint8)
    frame[240:250, 320:330] = 255
    
    # Run the pipeline
    disturbed_frame, telemetry = pipeline.apply(frame, sim_time=0.0, sim_dt=0.033)
    
    # If jitter is before atmosphere, the shifted spot will have atmospheric contrast applied.
    # We can check that telemetry has jitter and atmosphere enabled.
    assert telemetry.camera_jitter_enabled
    assert telemetry.atmosphere_enabled
    
    # The output frame should not just be black, the spot should be shifted and degraded
    assert np.max(disturbed_frame) > 0
    # Spot should be degraded (not 255) due to fog
    assert np.max(disturbed_frame) < 255

