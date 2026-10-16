"""FitSense AI - Biomechanical Math Utilities.

Pure, deterministic geometry and signal processing functions for:
- 3-point joint angle calculation
- Line-to-horizontal orientation angle
- Signed normalized hip deviation (pike/sag detection)
- Temporal moving-average smoothing for landmark coordinates
"""

import math
from collections import deque

from prototype.models import Landmark


def calculate_angle_3points(p1: Landmark, p2: Landmark, p3: Landmark) -> float:
    """Calculate the interior 2D angle (in degrees) at vertex p2 between p2->p1 and p2->p3.

    Formula:
        v1 = p1 - p2
        v2 = p3 - p2
        theta = arccos((v1 . v2) / (|v1| * |v2|)) * (180 / pi)
    Returns:
        float angle in range [0.0, 180.0] degrees.
    """
    v1_x = p1.x - p2.x
    v1_y = p1.y - p2.y
    v2_x = p3.x - p2.x
    v2_y = p3.y - p2.y

    dot_product = v1_x * v2_x + v1_y * v2_y
    mag1 = math.hypot(v1_x, v1_y)
    mag2 = math.hypot(v2_x, v2_y)

    if mag1 < 1e-7 or mag2 < 1e-7:
        return 0.0

    cosine = dot_product / (mag1 * mag2)
    # Clamp cosine to [-1.0, 1.0] for floating point stability
    cosine = max(-1.0, min(1.0, cosine))
    angle_rad = math.acos(cosine)
    return math.degrees(angle_rad)


def calculate_line_horizontal_angle(p1: Landmark, p2: Landmark) -> float:
    """Calculate the acute angle (in degrees) of segment p1->p2 with the horizontal axis.

    Used as the body orientation gate: shoulder-ankle line must be within
    MAX_BODY_HORIZONTAL_ANGLE_DEG (default 35 deg) of horizontal.
    """
    dx = p2.x - p1.x
    dy = p2.y - p1.y

    if abs(dx) < 1e-7 and abs(dy) < 1e-7:
        return 90.0

    angle_rad = math.atan2(abs(dy), abs(dx))
    return math.degrees(angle_rad)


def calculate_signed_hip_deviation(
    shoulder: Landmark, hip: Landmark, ankle: Landmark
) -> float:
    """Calculate signed normalized deviation of hip from the shoulder-ankle line.

    Sign Convention (Screen Coordinates, y increases downwards):
    - Positive (+): Hips elevated above shoulder-ankle line (PIKED).
    - Negative (-): Hips dropped below shoulder-ankle line (SAGGING).
    Normalized by torso length (Euclidean distance between shoulder and hip).
    """
    torso_len = math.hypot(hip.x - shoulder.x, hip.y - shoulder.y)
    if torso_len < 1e-6:
        return 0.0

    # Line from shoulder (x1, y1) to ankle (x2, y2)
    dx = ankle.x - shoulder.x
    dy = ankle.y - shoulder.y

    line_length = math.hypot(dx, dy)
    if line_length < 1e-6:
        return 0.0

    # If the user is lying horizontally, we interpolate the expected y-coordinate of the line at hip.x
    if abs(dx) > 1e-5:
        t = (hip.x - shoulder.x) / dx
        expected_line_y = shoulder.y + t * dy
        # In screen coords, smaller y is higher up.
        # So (expected_line_y - hip.y) > 0 means hip is higher than the line (piked).
        # (expected_line_y - hip.y) < 0 means hip is lower than the line (sagging).
        deviation = expected_line_y - hip.y
    else:
        # Fallback for near-vertical alignment: signed perpendicular distance
        # Standard 2D cross-product distance
        deviation = (
            -(dy * hip.x - dx * hip.y + ankle.x * shoulder.y - ankle.y * shoulder.x)
            / line_length
        )

    return deviation / torso_len


class LandmarkSmoother:
    """Sliding-window moving-average smoother for landmark coordinate streams."""

    def __init__(self, window_size: int = 5):
        self.window_size = max(1, window_size)
        self.history: deque[dict[int, Landmark]] = deque(maxlen=self.window_size)

    def reset(self) -> None:
        """Clear smoothing history."""
        self.history.clear()

    def smooth(
        self, landmarks: dict[int, Landmark], min_visibility: float = 0.5
    ) -> dict[int, Landmark]:
        """Apply temporal moving average across valid landmarks in the window.

        Landmarks with visibility below min_visibility are excluded from averaging.
        """
        self.history.append(landmarks)
        smoothed: dict[int, Landmark] = {}

        for idx, current_lm in landmarks.items():
            if current_lm.visibility < min_visibility:
                # Landmark quality too poor: preserve raw landmark with low visibility flag
                smoothed[idx] = current_lm
                continue

            sum_x = 0.0
            sum_y = 0.0
            sum_z = 0.0
            sum_vis = 0.0
            valid_count = 0

            for frame_lms in self.history:
                if idx in frame_lms and frame_lms[idx].visibility >= min_visibility:
                    lm = frame_lms[idx]
                    sum_x += lm.x
                    sum_y += lm.y
                    sum_z += lm.z
                    sum_vis += lm.visibility
                    valid_count += 1

            if valid_count > 0:
                smoothed[idx] = Landmark(
                    x=sum_x / valid_count,
                    y=sum_y / valid_count,
                    z=sum_z / valid_count,
                    visibility=sum_vis / valid_count,
                    presence=current_lm.presence,
                )
            else:
                smoothed[idx] = current_lm

        return smoothed
