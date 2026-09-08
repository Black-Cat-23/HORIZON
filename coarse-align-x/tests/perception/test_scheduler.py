import numpy as np
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.neural_detector import NeuralBeaconDetector
from simulator.perception.hybrid_fusion import HybridPerceptionFusion
from simulator.perception.scheduler import AdaptivePerceptionScheduler, SchedulerConfig


class MockClassicalDetector(ClassicalBeaconDetector):
    def __init__(self, detected=True, confidence=0.8, count=1):
        super().__init__()
        self.mock_detected = detected
        self.mock_confidence = confidence
        self.mock_count = count

    def detect(self, frame, timestamp=0.0, collect_diagnostics=False):
        return DetectionResult(
            detected=self.mock_detected,
            centroid=(320.0, 240.0) if self.mock_detected else None,
            bbox=None,
            confidence=self.mock_confidence,
            candidate_count=self.mock_count,
            method_used="mock_classical",
            processing_time_ms=3.0,
            timestamp=timestamp
        )


class MockNeuralDetector(NeuralBeaconDetector):
    def __init__(self, detected=True, confidence=0.9):
        super().__init__()
        self.mock_detected = detected
        self.mock_confidence = confidence
        self.call_count = 0

    def detect(self, frame, timestamp=0.0, collect_diagnostics=False):
        self.call_count += 1
        return DetectionResult(
            detected=self.mock_detected,
            centroid=(320.0, 240.0) if self.mock_detected else None,
            bbox=None,
            confidence=self.mock_confidence,
            candidate_count=1 if self.mock_detected else 0,
            method_used="mock_neural",
            processing_time_ms=30.0,
            timestamp=timestamp
        )


def setup_scheduler(classical=None, neural=None, config=None):
    c = classical or MockClassicalDetector()
    n = neural or MockNeuralDetector()
    f = HybridPerceptionFusion()
    return AdaptivePerceptionScheduler(c, n, f, config=config), c, n


def test_always_full_hybrid_outside_track():
    sched, _, neural = setup_scheduler()
    frame = np.zeros((480, 640), dtype=np.uint8)
    
    for mode in ("SEARCH", "ACQUIRE", "DEGRADED", "REACQUIRE"):
        neural.call_count = 0
        _, compute_mode = sched.detect(frame, 0.0, pat_mode=mode, track_quality=1.0, consecutive_hits=10)
        assert compute_mode == "FULL_HYBRID"
        assert neural.call_count == 1


def test_fast_path_when_stable_and_confident():
    sched, _, neural = setup_scheduler()
    frame = np.zeros((480, 640), dtype=np.uint8)
    
    _, compute_mode = sched.detect(frame, 0.0, pat_mode="TRACK", track_quality=0.8, consecutive_hits=6)
    
    assert compute_mode == "CLASSICAL_FAST_PATH"
    assert neural.call_count == 0


def test_recalibration_forces_full_hybrid_periodically():
    config = SchedulerConfig(recalibration_period_frames=3)
    sched, _, neural = setup_scheduler(config=config)
    frame = np.zeros((480, 640), dtype=np.uint8)
    
    modes = []
    for _ in range(4):
        _, mode = sched.detect(frame, 0.0, pat_mode="TRACK", track_quality=0.8, consecutive_hits=6)
        modes.append(mode)
        
    assert modes == [
        "CLASSICAL_FAST_PATH",
        "CLASSICAL_FAST_PATH",
        "CLASSICAL_FAST_PATH",
        "FULL_HYBRID"
    ]
    assert neural.call_count == 1


def test_escalates_on_ambiguous_classical_result():
    # Setup classical to return low confidence
    classical = MockClassicalDetector(confidence=0.3)
    sched, _, neural = setup_scheduler(classical=classical)
    frame = np.zeros((480, 640), dtype=np.uint8)
    
    _, compute_mode = sched.detect(frame, 0.0, pat_mode="TRACK", track_quality=0.8, consecutive_hits=6)
    
    # Despite being stable, the weak classical result should trigger escalation
    assert compute_mode == "FULL_HYBRID"
    assert neural.call_count == 1

    # Setup classical to return multiple candidates
    classical2 = MockClassicalDetector(confidence=0.9, count=2)
    sched2, _, neural2 = setup_scheduler(classical=classical2)
    _, compute_mode2 = sched2.detect(frame, 0.0, pat_mode="TRACK", track_quality=0.8, consecutive_hits=6)
    
    assert compute_mode2 == "FULL_HYBRID"
    assert neural2.call_count == 1


def test_scheduler_matches_full_hybrid_when_always_escalating():
    config = SchedulerConfig(recalibration_period_frames=1) # Forces full hybrid every frame
    sched, _, neural = setup_scheduler(config=config)
    frame = np.zeros((480, 640), dtype=np.uint8)
    
    res_sched, mode = sched.detect(frame, 0.0, pat_mode="TRACK", track_quality=0.8, consecutive_hits=6)
    
    # Directly call run_hybrid_fusion
    res_direct = sched.run_hybrid_fusion(frame, 0.0)
    
    assert mode == "FULL_HYBRID"
    assert res_sched.detected == res_direct.detected
    assert res_sched.confidence == res_direct.confidence
    assert neural.call_count == 2  # Once for sched, once for direct

