"""Synthetic Push-up Data Generator for Unit Testing & Parity Verification.

Generates realistic frame-by-frame 2D landmark sequences for:
- Clean complete push-ups
- Partial range (half) push-ups
- Technique errors: hips sagging and hips piked
- Temporal jitter and too-fast twitching
- Low confidence tracking and person leaving the frame
- Standing orientation (out-of-position)
"""

import math

from prototype.models import Landmark


def generate_frame_landmarks(
    elbow_angle_deg: float,
    hip_dev_offset: float = 0.0,
    body_angle_deg: float = 0.0,
    visibility: float = 0.95,
    side: str = "LEFT",
) -> dict[int, Landmark]:
    """Generate a 33-landmark pose dictionary corresponding to specific joint angles.

    Constructs 2D landmarks for a side-view push-up posture:
    - Shoulder positioned at (0.30, 0.50)
    - Ankle positioned at (0.80, 0.50 + tan(body_angle))
    - Hip positioned between shoulder and ankle with signed vertical offset
    - Elbow and Wrist positioned based on desired elbow angle
    """
    # Exact 2D inverse kinematics for arm:
    # Upper arm and forearm lengths L = 0.125
    # Wrist pinned to floor at (0.30, 0.75)
    w_x, w_y = 0.30, 0.75
    L = 0.125
    rad_elbow = math.radians(elbow_angle_deg)
    d = 2.0 * L * math.sin(rad_elbow / 2.0)
    h = L * math.cos(rad_elbow / 2.0)

    # Shoulder descends as arm folds
    s_x = 0.30
    s_y = w_y - d
    e_x = s_x - h
    e_y = (s_y + w_y) / 2.0

    # Body line from shoulder to ankle
    rad_body = math.radians(body_angle_deg)
    a_x = 0.80
    a_y = s_y + (a_x - s_x) * math.sin(rad_body)

    # Hip at midpoint with offset
    h_x = (s_x + a_x) / 2.0
    torso_len = math.hypot(h_x - s_x, (s_y + a_y) / 2.0 - s_y)
    line_y = s_y + (h_x - s_x) / (a_x - s_x) * (a_y - s_y)
    h_y = line_y - (hip_dev_offset * torso_len)

    # Knee at midpoint between hip and ankle
    k_x = (h_x + a_x) / 2.0
    k_y = (h_y + a_y) / 2.0

    # Populate 33 landmarks dictionary
    landmarks: dict[int, Landmark] = {}

    # Offsets for opposite side so dominant side selection works
    opp_vis = visibility * 0.4

    if side.upper() == "LEFT":
        # Left side is dominant
        landmarks[11] = Landmark(x=s_x, y=s_y, z=0.0, visibility=visibility)
        landmarks[13] = Landmark(x=e_x, y=e_y, z=0.0, visibility=visibility)
        landmarks[15] = Landmark(x=w_x, y=w_y, z=0.0, visibility=visibility)
        landmarks[23] = Landmark(x=h_x, y=h_y, z=0.0, visibility=visibility)
        landmarks[25] = Landmark(x=k_x, y=k_y, z=0.0, visibility=visibility)
        landmarks[27] = Landmark(x=a_x, y=a_y, z=0.0, visibility=visibility)

        # Right side with low visibility
        landmarks[12] = Landmark(x=s_x, y=s_y, z=0.1, visibility=opp_vis)
        landmarks[14] = Landmark(x=e_x, y=e_y, z=0.1, visibility=opp_vis)
        landmarks[16] = Landmark(x=w_x, y=w_y, z=0.1, visibility=opp_vis)
        landmarks[24] = Landmark(x=h_x, y=h_y, z=0.1, visibility=opp_vis)
        landmarks[26] = Landmark(x=k_x, y=k_y, z=0.1, visibility=opp_vis)
        landmarks[28] = Landmark(x=a_x, y=a_y, z=0.1, visibility=opp_vis)
    else:
        # Right side dominant
        landmarks[12] = Landmark(x=s_x, y=s_y, z=0.0, visibility=visibility)
        landmarks[14] = Landmark(x=e_x, y=e_y, z=0.0, visibility=visibility)
        landmarks[16] = Landmark(x=w_x, y=w_y, z=0.0, visibility=visibility)
        landmarks[24] = Landmark(x=h_x, y=h_y, z=0.0, visibility=visibility)
        landmarks[26] = Landmark(x=k_x, y=k_y, z=0.0, visibility=visibility)
        landmarks[28] = Landmark(x=a_x, y=a_y, z=0.0, visibility=visibility)

        landmarks[11] = Landmark(x=s_x, y=s_y, z=0.1, visibility=opp_vis)
        landmarks[13] = Landmark(x=e_x, y=e_y, z=0.1, visibility=opp_vis)
        landmarks[15] = Landmark(x=w_x, y=w_y, z=0.1, visibility=opp_vis)
        landmarks[23] = Landmark(x=h_x, y=h_y, z=0.1, visibility=opp_vis)
        landmarks[25] = Landmark(x=k_x, y=k_y, z=0.1, visibility=opp_vis)
        landmarks[27] = Landmark(x=a_x, y=a_y, z=0.1, visibility=opp_vis)

    return landmarks


def generate_pushup_stream(
    num_reps: int = 1,
    min_elbow_angle: float = 85.0,
    rep_duration_s: float = 1.5,
    hip_dev: float = 0.0,
    body_angle_deg: float = 5.0,
    visibility: float = 0.95,
    fps: float = 30.0,
    start_time_s: float = 0.0,
) -> list[tuple[float, dict[int, Landmark]]]:
    """Generate a continuous timestamped stream of frames for push-up repetitions."""
    frames_per_rep = int(rep_duration_s * fps)
    stream: list[tuple[float, dict[int, Landmark]]] = []
    current_time = start_time_s
    dt = 1.0 / fps

    # Initial resting frames at lockout (165 deg)
    for _ in range(int(fps * 0.5)):
        lms = generate_frame_landmarks(
            elbow_angle_deg=165.0,
            hip_dev_offset=hip_dev,
            body_angle_deg=body_angle_deg,
            visibility=visibility,
        )
        stream.append((current_time, lms))
        current_time += dt

    for _ in range(num_reps):
        # Half cycle lowering: 165 down to min_elbow_angle
        half_frames = frames_per_rep // 2
        for i in range(half_frames):
            t = i / half_frames
            angle = 165.0 - (165.0 - min_elbow_angle) * (
                1.0 - math.cos(t * math.pi / 2.0)
            )
            lms = generate_frame_landmarks(
                elbow_angle_deg=angle,
                hip_dev_offset=hip_dev,
                body_angle_deg=body_angle_deg,
                visibility=visibility,
            )
            stream.append((current_time, lms))
            current_time += dt

        # Half cycle raising: min_elbow_angle up to 165
        for i in range(half_frames):
            t = i / half_frames
            angle = min_elbow_angle + (165.0 - min_elbow_angle) * math.sin(
                t * math.pi / 2.0
            )
            lms = generate_frame_landmarks(
                elbow_angle_deg=angle,
                hip_dev_offset=hip_dev,
                body_angle_deg=body_angle_deg,
                visibility=visibility,
            )
            stream.append((current_time, lms))
            current_time += dt

        # Brief top pause (0.2s)
        for _ in range(int(fps * 0.2)):
            lms = generate_frame_landmarks(
                elbow_angle_deg=165.0,
                hip_dev_offset=hip_dev,
                body_angle_deg=body_angle_deg,
                visibility=visibility,
            )
            stream.append((current_time, lms))
            current_time += dt

    return stream
