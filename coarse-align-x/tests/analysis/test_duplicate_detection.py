"""
Test Duplicate Detection
"""
from analysis.validation.duplicate_detector import DuplicateDetector

def test_duplicate_detector():
    detector = DuplicateDetector()
    trials = [
        {"algorithm": "OURS", "seed": 42, "scenario_id": "NOMINAL"},
        {"algorithm": "OURS", "seed": 42, "scenario_id": "NOMINAL"},
    ]
    dups = detector.find_duplicates(trials)
    assert len(dups) == 1
