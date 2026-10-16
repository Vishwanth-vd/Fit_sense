"""FitSense AI - Centralized Push-up Biomechanics Configuration.

All thresholds and parameters for pose filtering, feature extraction,
finite state machine hysteresis, baseline calibration, and voice rate-limiting
are declared here. No thresholds are hard-coded in analyzer logic.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PushUpConfig:
    """Configurable thresholds for Push-up detection and form assessment."""

    # Landmark indices according to MediaPipe Pose 33-landmark schema
    LEFT_SHOULDER: int = 11
    RIGHT_SHOULDER: int = 12
    LEFT_ELBOW: int = 13
    RIGHT_ELBOW: int = 14
    LEFT_WRIST: int = 15
    RIGHT_WRIST: int = 16
    LEFT_HIP: int = 23
    RIGHT_HIP: int = 24
    LEFT_KNEE: int = 25
    RIGHT_KNEE: int = 26
    LEFT_ANKLE: int = 27
    RIGHT_ANKLE: int = 28

    # Side selection indices
    LEFT_BODY_LANDMARKS: list[int] = field(
        default_factory=lambda: [11, 13, 15, 23, 25, 27]
    )
    RIGHT_BODY_LANDMARKS: list[int] = field(
        default_factory=lambda: [12, 14, 16, 24, 26, 28]
    )

    # Filtering & Smoothing
    MIN_LANDMARK_VISIBILITY: float = 0.5  # Below this, landmark is ignored
    SMOOTHING_WINDOW_SIZE: int = 5  # Moving average window size in frames

    # Pose Gate: Body Orientation
    MAX_BODY_HORIZONTAL_ANGLE_DEG: float = 35.0  # Shoulder-ankle line to horizontal

    # State Machine Hysteresis Thresholds (Elbow angle in degrees)
    ELBOW_ANGLE_UP: float = 155.0  # Must be >= 155 to be in UP state
    ELBOW_ANGLE_DOWN: float = 95.0  # Must be <= 95 to reach DOWN state
    LOWERING_HYSTERESIS_OFFSET: float = 5.0  # Transition buffer to LOWERING (< 150)
    RAISING_HYSTERESIS_OFFSET: float = 5.0  # Transition buffer to RAISING (> 100)

    # Temporal & Repetition Constraints
    MIN_REP_DURATION_SEC: float = 0.8  # Reps faster than this are flagged too_fast
    MAX_REP_DURATION_SEC: float = 7.0  # Rep timeout / stall

    # Form Thresholds
    BODY_LINE_ANGLE_MIN_DEG: float = 160.0  # Straight plank expected ~180
    HIP_SAG_THRESHOLD: float = -0.15  # Signed normalized hip deviation < -0.15
    HIP_PIKE_THRESHOLD: float = 0.15  # Signed normalized hip deviation > +0.15

    # Low-Confidence & Baseline Rules
    MIN_REP_MEAN_VISIBILITY: float = 0.6  # Below 0.6 -> marked low_confidence
    BASELINE_CALIBRATION_REPS: int = 5  # First N valid reps build the baseline
    BASELINE_EPSILON: float = 1e-4  # Epsilon for std division
    Z_SCORE_DEVIATION_THRESHOLD: float = 2.0  # |z| > 2 flags anomaly
    CONSECUTIVE_ANOMALIES_TO_ALERT: int = 3  # Must persist for 3 consecutive reps

    # Audio Feedback & Rate Limiting
    VOICE_CUE_COOLDOWN_SEC: float = 5.0  # At most 1 spoken cue every 5 seconds

    # Camera Setup Verification
    SETUP_MIN_BODY_VISIBILITY: float = 0.65  # Overall landmark visibility in setup
    SETUP_MAX_TILT_DEG: float = 40.0  # Setup side-on plane tolerance
