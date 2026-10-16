"""Comprehensive unit tests for PushUpAnalyzer state machine and rules."""

from prototype.analyzer import PushUpAnalyzer
from prototype.config import PushUpConfig
from prototype.models import FormFlag, RepState
from prototype.tests.synthetic_data import (
    generate_frame_landmarks,
    generate_pushup_stream,
)


def test_clean_reps_counting():
    """Verify 3 consecutive clean push-up repetitions are counted correctly."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    stream = generate_pushup_stream(
        num_reps=3,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        hip_dev=0.0,
        visibility=0.95,
        fps=30.0,
    )

    reps_detected = []
    for timestamp_s, landmarks in stream:
        _, rep, _ = analyzer.process_frame(landmarks, timestamp_s)
        if rep:
            reps_detected.append(rep)

    assert len(reps_detected) == 3
    assert analyzer.rep_count == 3
    assert analyzer.clean_rep_count == 3

    for r in reps_detected:
        assert r.is_clean is True
        assert len(r.flags) == 0
        assert r.min_elbow_angle <= 95.0
        assert r.duration_s >= 0.8
        assert r.low_confidence is False


def test_partial_range_rep():
    """Verify rep that fails to reach 95 deg is flagged as partial_range and not clean."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=115.0,  # Fails to reach <= 95
        rep_duration_s=1.5,
        hip_dev=0.0,
        fps=30.0,
    )

    completed_reps = []
    for timestamp_s, landmarks in stream:
        _, rep, _ = analyzer.process_frame(landmarks, timestamp_s)
        if rep:
            completed_reps.append(rep)

    assert len(completed_reps) == 1
    rep = completed_reps[0]
    assert rep.is_clean is False
    assert FormFlag.PARTIAL_RANGE.value in rep.flags
    assert analyzer.clean_rep_count == 0
    assert analyzer.rep_count == 1


def test_hips_sagging_flag():
    """Verify hip sag (negative deviation) triggers hips_sagging flag."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        hip_dev=-0.25,  # Hips sagging downwards (< -0.15 threshold)
        fps=30.0,
    )

    reps = []
    for timestamp_s, landmarks in stream:
        _, rep, _ = analyzer.process_frame(landmarks, timestamp_s)
        if rep:
            reps.append(rep)

    assert len(reps) == 1
    assert FormFlag.HIPS_SAGGING.value in reps[0].flags
    assert reps[0].is_clean is False


def test_hips_piked_flag():
    """Verify piked hips (positive deviation) triggers hips_piked flag."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        hip_dev=0.25,  # Hips piked upwards (> +0.15 threshold)
        fps=30.0,
    )

    reps = []
    for timestamp_s, landmarks in stream:
        _, rep, _ = analyzer.process_frame(landmarks, timestamp_s)
        if rep:
            reps.append(rep)

    assert len(reps) == 1
    assert FormFlag.HIPS_PIKED.value in reps[0].flags
    assert reps[0].is_clean is False


def test_too_fast_rep():
    """Verify rep under 0.8s duration is flagged too_fast."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=0.5,  # 0.5s < 0.8s minimum
        fps=30.0,
    )

    reps = []
    for timestamp_s, landmarks in stream:
        _, rep, _ = analyzer.process_frame(landmarks, timestamp_s)
        if rep:
            reps.append(rep)

    assert len(reps) == 1
    assert FormFlag.TOO_FAST.value in reps[0].flags
    assert reps[0].is_clean is False


def test_low_confidence_rule():
    """Verify mean visibility < 0.6 marks rep as low_confidence."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        visibility=0.52,  # > 0.5 minimum for tracking, but < 0.6 confidence
        fps=30.0,
    )

    reps = []
    for timestamp_s, landmarks in stream:
        _, rep, _ = analyzer.process_frame(landmarks, timestamp_s)
        if rep:
            reps.append(rep)

    assert len(reps) == 1
    assert reps[0].low_confidence is True
    assert FormFlag.LOW_CONFIDENCE.value in reps[0].flags


def test_body_orientation_standing_rejected():
    """Verify user standing upright (body orientation > 35 deg) counts no reps."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    # Generate stream with body tilted 75 degrees (standing upright)
    stream = generate_pushup_stream(
        num_reps=2,
        min_elbow_angle=85.0,
        body_angle_deg=75.0,  # Standing upright
        fps=30.0,
    )

    reps = []
    for timestamp_s, landmarks in stream:
        features, rep, _ = analyzer.process_frame(landmarks, timestamp_s)
        if features:
            assert features.is_in_pushup_position is False
        if rep:
            reps.append(rep)

    assert len(reps) == 0
    assert analyzer.rep_count == 0


def test_person_leaving_frame_abandons_rep():
    """Verify when person leaves frame during lowering, incomplete rep is abandoned."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())
    fps = 30.0
    dt = 1.0 / fps
    current_time = 0.0

    # Start in UP position
    for _ in range(15):
        lms = generate_frame_landmarks(165.0, visibility=0.95)
        analyzer.process_frame(lms, current_time)
        current_time += dt

    # Lower to 120 deg (in LOWERING state)
    for _ in range(10):
        lms = generate_frame_landmarks(120.0, visibility=0.95)
        analyzer.process_frame(lms, current_time)
        current_time += dt
    assert analyzer.state == RepState.LOWERING

    # Person disappears: empty landmarks for 2.0 seconds (> 1.5s timeout)
    for _ in range(int(fps * 2.0)):
        analyzer.process_frame({}, current_time)
        current_time += dt

    # State must reset to UP without recording a rep
    assert analyzer.state == RepState.UP
    assert analyzer.rep_count == 0
