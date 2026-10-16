"""Unit tests for VoiceAdvisor coaching cues and rate-limiting."""

from prototype.config import PushUpConfig
from prototype.models import FormFlag, Repetition
from prototype.voice_advisor import VoiceAdvisor


def create_test_rep(n: int, flags=None, low_conf: bool = False) -> Repetition:
    f = flags or []
    return Repetition(
        n=n,
        duration_s=1.5,
        down_duration_s=0.75,
        up_duration_s=0.75,
        down_up_tempo=1.0,
        min_elbow_angle=85.0,
        mean_body_line_angle=175.0,
        max_hip_deviation=0.0,
        mean_visibility=0.45 if low_conf else 0.9,
        is_clean=(len(f) == 0 and not low_conf),
        low_confidence=low_conf,
        flags=f,
    )


def test_voice_advisor_clean_rep_counting():
    advisor = VoiceAdvisor(config=PushUpConfig())

    cue1 = advisor.get_rep_feedback(create_test_rep(1), current_time_sec=10.0)
    assert cue1 == "One"

    # Next rep after 6 seconds (> 5s cooldown) -> speaks "Two"
    cue2 = advisor.get_rep_feedback(create_test_rep(2), current_time_sec=16.0)
    assert cue2 == "Two"


def test_voice_advisor_rate_limiting():
    advisor = VoiceAdvisor(config=PushUpConfig())

    # First cue at 10.0s
    cue1 = advisor.get_rep_feedback(create_test_rep(1), current_time_sec=10.0)
    assert cue1 == "One"

    # Second rep completes at 12.0s (only 2s elapsed < 5s cooldown) -> suppressed
    cue2 = advisor.get_rep_feedback(
        create_test_rep(2, flags=[FormFlag.PARTIAL_RANGE.value]),
        current_time_sec=12.0,
    )
    assert cue2 is None

    # Third rep completes at 15.5s (5.5s elapsed > 5s cooldown) -> allowed!
    cue3 = advisor.get_rep_feedback(
        create_test_rep(3, flags=[FormFlag.PARTIAL_RANGE.value]),
        current_time_sec=15.5,
    )
    assert cue3 == "Go a little lower"


def test_voice_advisor_error_cue_priority():
    advisor = VoiceAdvisor(config=PushUpConfig())

    # Form flag should produce coaching cue instead of rep count
    rep_sag = create_test_rep(1, flags=[FormFlag.HIPS_SAGGING.value])
    cue = advisor.get_rep_feedback(rep_sag, current_time_sec=10.0)
    assert cue == "Keep your hips up"


def test_voice_advisor_low_confidence_suppressed():
    advisor = VoiceAdvisor(config=PushUpConfig())

    # Low confidence rep should receive NO audio feedback
    rep_low_conf = create_test_rep(1, low_conf=True)
    cue = advisor.get_rep_feedback(rep_low_conf, current_time_sec=10.0)
    assert cue is None
