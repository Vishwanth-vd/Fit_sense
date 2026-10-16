"""FitSense AI - Data Models and Structures for Push-up Biomechanics.

Defines typed representations for landmarks, extracted frame features,
repetition states, form flags, and personal baseline statistics.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RepState(StrEnum):
    """Finite state machine states for push-up repetition cycles."""

    UP = "UP"
    LOWERING = "LOWERING"
    DOWN = "DOWN"
    RAISING = "RAISING"


class DominantSide(StrEnum):
    """Body side tracked based on camera view and visibility scores."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UNKNOWN = "UNKNOWN"


class FormFlag(StrEnum):
    """Rule-based flags for push-up technique deviations."""

    PARTIAL_RANGE = "partial_range"
    HIPS_SAGGING = "hips_sagging"
    HIPS_PIKED = "hips_piked"
    TOO_FAST = "too_fast"
    LOW_CONFIDENCE = "low_confidence"


@dataclass
class Landmark:
    """Individual 2D/3D body landmark from MediaPipe Pose."""

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0
    presence: float = 1.0

    def to_dict(self) -> dict[str, float]:
        return {
            "x": round(self.x, 5),
            "y": round(self.y, 5),
            "z": round(self.z, 5),
            "visibility": round(self.visibility, 5),
            "presence": round(self.presence, 5),
        }


@dataclass
class FrameFeatures:
    """Biomechanical angles and metrics extracted from a single frame."""

    timestamp_ms: float
    elbow_angle: float
    body_line_angle: float
    hip_deviation: float  # Signed perpendicular distance / torso length
    body_horizontal_angle: float  # Deviation of shoulder-ankle from horizontal
    mean_visibility: float
    dominant_side: DominantSide
    is_in_pushup_position: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ms": round(self.timestamp_ms, 2),
            "elbow_angle": round(self.elbow_angle, 2),
            "body_line_angle": round(self.body_line_angle, 2),
            "hip_deviation": round(self.hip_deviation, 4),
            "body_horizontal_angle": round(self.body_horizontal_angle, 2),
            "mean_visibility": round(self.mean_visibility, 4),
            "dominant_side": self.dominant_side.value,
            "is_in_pushup_position": self.is_in_pushup_position,
        }


@dataclass
class Repetition:
    """Completed repetition metrics, classification, and flags."""

    n: int
    duration_s: float
    down_duration_s: float
    up_duration_s: float
    down_up_tempo: float
    min_elbow_angle: float
    mean_body_line_angle: float
    max_hip_deviation: float
    mean_visibility: float
    is_clean: bool
    low_confidence: bool
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "duration_s": round(self.duration_s, 3),
            "down_duration_s": round(self.down_duration_s, 3),
            "up_duration_s": round(self.up_duration_s, 3),
            "down_up_tempo": round(self.down_up_tempo, 3),
            "min_elbow_angle": round(self.min_elbow_angle, 2),
            "body_line_angle": round(self.mean_body_line_angle, 2),
            "hip_deviation": round(self.max_hip_deviation, 4),
            "confidence": round(self.mean_visibility, 4),
            "is_clean": self.is_clean,
            "flags": self.flags,
        }


@dataclass
class BaselineMetricStats:
    """Summary statistics (mean, std) for a single metric."""

    mean: float
    std: float

    def to_dict(self) -> dict[str, float]:
        return {"mean": round(self.mean, 4), "std": round(self.std, 4)}


@dataclass
class UserBaseline:
    """User's calibrated baseline computed over initial non-low-confidence reps."""

    exercise_type: str = "pushup"
    is_calibrated: bool = False
    calibration_reps_count: int = 0
    feature_stats: dict[str, BaselineMetricStats] = field(default_factory=dict)
    consecutive_anomalies: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exercise_type": self.exercise_type,
            "is_calibrated": self.is_calibrated,
            "calibration_reps_count": self.calibration_reps_count,
            "feature_stats": {k: v.to_dict() for k, v in self.feature_stats.items()},
            "consecutive_anomalies": self.consecutive_anomalies,
        }
