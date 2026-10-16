"""Unit tests for Personal Baseline calibration and z-score anomaly detection."""

from prototype.baseline import PersonalBaselineTracker
from prototype.config import PushUpConfig
from prototype.models import Repetition


def make_rep(
    n: int, min_elbow: float = 85.0, duration: float = 1.5, low_conf: bool = False
) -> Repetition:
    return Repetition(
        n=n,
        duration_s=duration,
        down_duration_s=duration * 0.5,
        up_duration_s=duration * 0.5,
        down_up_tempo=1.0,
        min_elbow_angle=min_elbow,
        mean_body_line_angle=175.0,
        max_hip_deviation=0.02,
        mean_visibility=0.5 if low_conf else 0.9,
        is_clean=True,
        low_confidence=low_conf,
        flags=["low_confidence"] if low_conf else [],
    )


def test_baseline_calibration_first_5_reps():
    tracker = PersonalBaselineTracker(config=PushUpConfig())
    assert tracker.is_calibrated is False

    # First 4 reps: not yet calibrated
    for i in range(1, 5):
        alert, z = tracker.add_repetition(make_rep(i, min_elbow=85.0, duration=1.5))
        assert alert is False
        assert len(z) == 0
        assert tracker.is_calibrated is False

    # 5th rep: becomes calibrated
    alert, z = tracker.add_repetition(make_rep(5, min_elbow=85.0, duration=1.5))
    assert alert is False
    assert tracker.is_calibrated is True
    assert "min_elbow_angle" in tracker.baseline.feature_stats
    stats = tracker.baseline.feature_stats["min_elbow_angle"]
    assert stats.mean == 85.0


def test_baseline_low_confidence_reps_excluded():
    tracker = PersonalBaselineTracker(config=PushUpConfig())

    # Add 4 normal reps and 3 low confidence reps
    for i in range(1, 5):
        tracker.add_repetition(
            make_rep(i, min_elbow=85.0, duration=1.5, low_conf=False)
        )

    # Add low-confidence reps
    for i in range(5, 8):
        alert, z = tracker.add_repetition(
            make_rep(i, min_elbow=85.0, duration=1.5, low_conf=True)
        )
        assert alert is False
        assert len(z) == 0

    # Still not calibrated because only 4 valid reps
    assert tracker.is_calibrated is False

    # Add 5th valid rep
    tracker.add_repetition(make_rep(8, min_elbow=85.0, duration=1.5, low_conf=False))
    assert tracker.is_calibrated is True


def test_baseline_consecutive_anomaly_alert():
    tracker = PersonalBaselineTracker(config=PushUpConfig())

    # Calibrate with 5 reps having slight variations
    durations = [1.5, 1.6, 1.4, 1.5, 1.5]
    for i, d in enumerate(durations, start=1):
        tracker.add_repetition(make_rep(i, min_elbow=85.0, duration=d))
    assert tracker.is_calibrated is True

    # Rep 6: Normal rep -> no alert
    alert, z = tracker.add_repetition(make_rep(6, min_elbow=85.0, duration=1.5))
    assert alert is False
    assert tracker.consecutive_anomalies == 0

    # Rep 7: Massive anomaly (|z| > 2) -> 1 consecutive
    alert, z = tracker.add_repetition(make_rep(7, min_elbow=50.0, duration=5.0))
    assert alert is False
    assert tracker.consecutive_anomalies == 1

    # Rep 8: Massive anomaly -> 2 consecutive
    alert, z = tracker.add_repetition(make_rep(8, min_elbow=50.0, duration=5.0))
    assert alert is False
    assert tracker.consecutive_anomalies == 2

    # Rep 9: Massive anomaly -> 3 consecutive -> ALERT TRIGGERED!
    alert, z = tracker.add_repetition(make_rep(9, min_elbow=50.0, duration=5.0))
    assert alert is True
    assert tracker.consecutive_anomalies == 3

    # Rep 10: Returns to normal -> resets counter
    alert, z = tracker.add_repetition(make_rep(10, min_elbow=85.0, duration=1.5))
    assert alert is False
    assert tracker.consecutive_anomalies == 0
