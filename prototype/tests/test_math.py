"""Unit tests for biomechanics math and smoothing utilities."""

import pytest

from prototype.math_utils import (
    LandmarkSmoother,
    calculate_angle_3points,
    calculate_line_horizontal_angle,
    calculate_signed_hip_deviation,
)
from prototype.models import Landmark


def test_calculate_angle_right_angle():
    # Shoulder at (0, 1), Elbow at (0, 0), Wrist at (1, 0) -> 90 degrees
    p1 = Landmark(x=0.0, y=1.0)
    p2 = Landmark(x=0.0, y=0.0)
    p3 = Landmark(x=1.0, y=0.0)
    angle = calculate_angle_3points(p1, p2, p3)
    assert pytest.approx(angle, abs=1e-3) == 90.0


def test_calculate_angle_straight_line():
    # Straight arm: Shoulder at (0, 0), Elbow at (1, 0), Wrist at (2, 0) -> 180 degrees
    p1 = Landmark(x=0.0, y=0.0)
    p2 = Landmark(x=1.0, y=0.0)
    p3 = Landmark(x=2.0, y=0.0)
    angle = calculate_angle_3points(p1, p2, p3)
    assert pytest.approx(angle, abs=1e-3) == 180.0


def test_calculate_angle_collinear_reversal():
    # Folded arm: Shoulder at (1, 0), Elbow at (0, 0), Wrist at (1, 0) -> 0 degrees
    p1 = Landmark(x=1.0, y=0.0)
    p2 = Landmark(x=0.0, y=0.0)
    p3 = Landmark(x=1.0, y=0.0)
    angle = calculate_angle_3points(p1, p2, p3)
    assert pytest.approx(angle, abs=1e-3) == 0.0


def test_calculate_line_horizontal_angle():
    # Horizontal line: shoulder (0.2, 0.5), ankle (0.8, 0.5) -> 0 deg
    s = Landmark(x=0.2, y=0.5)
    a = Landmark(x=0.8, y=0.5)
    assert pytest.approx(calculate_line_horizontal_angle(s, a), abs=1e-3) == 0.0

    # Vertical line: standing upright -> 90 deg
    s_vert = Landmark(x=0.5, y=0.2)
    a_vert = Landmark(x=0.5, y=0.8)
    assert (
        pytest.approx(calculate_line_horizontal_angle(s_vert, a_vert), abs=1e-3) == 90.0
    )

    # 45-degree angle
    s_45 = Landmark(x=0.0, y=0.0)
    a_45 = Landmark(x=1.0, y=1.0)
    assert pytest.approx(calculate_line_horizontal_angle(s_45, a_45), abs=1e-3) == 45.0


def test_calculate_signed_hip_deviation():
    # Shoulder at (0.2, 0.5), Ankle at (0.8, 0.5)
    shoulder = Landmark(x=0.2, y=0.5)
    ankle = Landmark(x=0.8, y=0.5)

    # Perfect straight plank: Hip at (0.5, 0.5) -> dev = 0
    hip_straight = Landmark(x=0.5, y=0.5)
    dev_straight = calculate_signed_hip_deviation(shoulder, hip_straight, ankle)
    assert pytest.approx(dev_straight, abs=1e-3) == 0.0

    # Sagging hips: Hip drops towards floor (y=0.6, higher screen y) -> negative dev
    hip_sag = Landmark(x=0.5, y=0.6)
    dev_sag = calculate_signed_hip_deviation(shoulder, hip_sag, ankle)
    assert dev_sag < -0.1

    # Piked hips: Hip raises towards ceiling (y=0.4, lower screen y) -> positive dev
    hip_pike = Landmark(x=0.5, y=0.4)
    dev_pike = calculate_signed_hip_deviation(shoulder, hip_pike, ankle)
    assert dev_pike > 0.1


def test_landmark_smoother():
    smoother = LandmarkSmoother(window_size=3)

    # Frame 1: x = 10
    f1 = {11: Landmark(x=10.0, y=5.0, visibility=0.9)}
    s1 = smoother.smooth(f1)
    assert pytest.approx(s1[11].x, abs=1e-3) == 10.0

    # Frame 2: x = 20 -> average = 15
    f2 = {11: Landmark(x=20.0, y=5.0, visibility=0.9)}
    s2 = smoother.smooth(f2)
    assert pytest.approx(s2[11].x, abs=1e-3) == 15.0

    # Frame 3: x = 30 -> average = 20
    f3 = {11: Landmark(x=30.0, y=5.0, visibility=0.9)}
    s3 = smoother.smooth(f3)
    assert pytest.approx(s3[11].x, abs=1e-3) == 20.0

    # Low visibility frame (0.3) ignored from moving average
    f4 = {11: Landmark(x=100.0, y=5.0, visibility=0.3)}
    s4 = smoother.smooth(f4, min_visibility=0.5)
    assert s4[11].visibility == 0.3
