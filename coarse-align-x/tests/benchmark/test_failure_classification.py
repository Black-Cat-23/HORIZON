"""
Unit tests for FailureClassifier.
"""

from benchmark.failure import FailureClassifier, FailureCategory


def test_failure_classification_categories():
    classifier = FailureClassifier(max_mean_error_px=20.0)

    # 1. Runtime error exception
    cat_err = classifier.classify_trial({}, exception=RuntimeError("Crash"))
    assert cat_err == FailureCategory.RUNTIME_ERROR

    # 2. No acquisition
    cat_no_acq = classifier.classify_trial({"acquisition_time": None})
    assert cat_no_acq == FailureCategory.NO_ACQUISITION

    # 3. Excessive error
    cat_exc = classifier.classify_trial({"acquisition_time": 0.1, "mean_tracking_error": 35.0})
    assert cat_exc == FailureCategory.EXCESSIVE_ERROR

    # 4. Success
    cat_succ = classifier.classify_trial({
        "acquisition_time": 0.1,
        "mean_tracking_error": 5.0,
        "lock_retention_rate": 0.95,
        "P95_processing_time": 10.0,
    })
    assert cat_succ == FailureCategory.SUCCESS
