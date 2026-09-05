"""
Test Failure Analysis & Taxonomy
"""
from analysis.failures.classifier import FailureClassifier, FailureMode

def test_failure_classifier():
    classifier = FailureClassifier()
    trial = {"status": "SUCCESS", "metrics": {"mean_tracking_error_px": 100.0}}
    mode = classifier.classify_trial(trial)
    assert mode == FailureMode.EXCESSIVE_ERROR
