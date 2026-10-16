"""FitSense AI - Golden JSON Test Vectors Exporter.

Executes PushUpAnalyzer across comprehensive synthetic scenarios and exports
the exact frame streams and expected outputs to `prototype/vectors/golden_vectors.json`.
The Dart test suite in Phase P3 will load this exact JSON file to verify bit-level parity.
"""

import json
from pathlib import Path
from typing import Any

from prototype.analyzer import PushUpAnalyzer
from prototype.config import PushUpConfig
from prototype.models import Landmark
from prototype.tests.synthetic_data import (
    generate_frame_landmarks,
    generate_pushup_stream,
)


def run_scenario(
    stream: list[tuple[float, dict[int, Landmark]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run PushUpAnalyzer on a stream and serialize frames and results."""
    analyzer = PushUpAnalyzer(config=PushUpConfig())

    input_frames = []
    for timestamp_s, landmarks in stream:
        lms_dict = {str(k): lm.to_dict() for k, lm in landmarks.items()}
        input_frames.append(
            {
                "timestamp_s": round(timestamp_s, 4),
                "landmarks": lms_dict,
            }
        )
        analyzer.process_frame(landmarks, timestamp_s)

    expected_output = {
        "rep_count": analyzer.rep_count,
        "clean_rep_count": analyzer.clean_rep_count,
        "final_state": analyzer.state.value,
        "completed_reps": [r.to_dict() for r in analyzer.completed_reps],
    }

    return input_frames, expected_output


def generate_all_golden_vectors() -> dict[str, Any]:
    """Generate all test scenarios."""
    scenarios: dict[str, Any] = {}

    # Scenario 1: Clean repetitions (3 clean push-ups)
    s1_stream = generate_pushup_stream(
        num_reps=3,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        hip_dev=0.0,
        visibility=0.95,
        fps=30.0,
    )
    in1, out1 = run_scenario(s1_stream)
    scenarios["clean_reps"] = {
        "description": "Three consecutive clean push-ups with full ROM (elbow <= 95) and proper plank posture.",
        "input_frames": in1,
        "expected_output": out1,
    }

    # Scenario 2: Partial range repetition (half rep, reaches only 115 deg)
    s2_stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=115.0,
        rep_duration_s=1.5,
        hip_dev=0.0,
        visibility=0.95,
        fps=30.0,
    )
    in2, out2 = run_scenario(s2_stream)
    scenarios["partial_reps"] = {
        "description": "One repetition that fails to reach down threshold (<= 95 deg). Flagged partial_range.",
        "input_frames": in2,
        "expected_output": out2,
    }

    # Scenario 3: Hips sagging (negative deviation)
    s3_stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        hip_dev=-0.25,
        visibility=0.95,
        fps=30.0,
    )
    in3, out3 = run_scenario(s3_stream)
    scenarios["hips_sagging"] = {
        "description": "One repetition with sagging hips (hip deviation < -0.15). Flagged hips_sagging.",
        "input_frames": in3,
        "expected_output": out3,
    }

    # Scenario 4: Hips piked (positive deviation)
    s4_stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        hip_dev=0.25,
        visibility=0.95,
        fps=30.0,
    )
    in4, out4 = run_scenario(s4_stream)
    scenarios["hips_piked"] = {
        "description": "One repetition with piked hips (hip deviation > +0.15). Flagged hips_piked.",
        "input_frames": in4,
        "expected_output": out4,
    }

    # Scenario 5: Too fast repetition (duration < 0.8s)
    s5_stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=0.5,
        hip_dev=0.0,
        visibility=0.95,
        fps=30.0,
    )
    in5, out5 = run_scenario(s5_stream)
    scenarios["too_fast"] = {
        "description": "One twitching repetition faster than 0.8s minimum duration. Flagged too_fast.",
        "input_frames": in5,
        "expected_output": out5,
    }

    # Scenario 6: Low confidence tracking (mean visibility < 0.6)
    s6_stream = generate_pushup_stream(
        num_reps=1,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        hip_dev=0.0,
        visibility=0.52,
        fps=30.0,
    )
    in6, out6 = run_scenario(s6_stream)
    scenarios["low_confidence"] = {
        "description": "One repetition with mean visibility below 0.6. Flagged low_confidence.",
        "input_frames": in6,
        "expected_output": out6,
    }

    # Scenario 7: Person standing upright (body orientation > 35 deg from horizontal)
    s7_stream = generate_pushup_stream(
        num_reps=2,
        min_elbow_angle=85.0,
        rep_duration_s=1.5,
        body_angle_deg=75.0,
        fps=30.0,
    )
    in7, out7 = run_scenario(s7_stream)
    scenarios["standing_upright"] = {
        "description": "User standing upright. Orientation gate blocks push-up counting; 0 reps detected.",
        "input_frames": in7,
        "expected_output": out7,
    }

    # Scenario 8: Person leaving frame (incomplete rep abandoned after 1.5s loss)
    s8_stream: list[tuple[float, dict[int, Landmark]]] = []
    dt = 1.0 / 30.0
    t = 0.0
    # 15 frames in UP
    for _ in range(15):
        s8_stream.append((t, generate_frame_landmarks(165.0, visibility=0.95)))
        t += dt
    # 10 frames in LOWERING
    for _ in range(10):
        s8_stream.append((t, generate_frame_landmarks(120.0, visibility=0.95)))
        t += dt
    # 60 frames empty (person walked away)
    for _ in range(60):
        s8_stream.append((t, {}))
        t += dt

    in8, out8 = run_scenario(s8_stream)
    scenarios["frame_exit"] = {
        "description": "Person leaves camera frame during lowering. Repetition abandoned; 0 reps detected.",
        "input_frames": in8,
        "expected_output": out8,
    }

    return scenarios


def main():
    output_dir = Path("prototype/vectors")
    output_dir.mkdir(parents=True, exist_ok=True)
    golden_path = output_dir / "golden_vectors.json"

    print("[INFO] Generating golden test vectors for Dart parity...")
    scenarios = generate_all_golden_vectors()

    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2)

    total_scenarios = len(scenarios)
    total_frames = sum(len(s["input_frames"]) for s in scenarios.values())
    print(
        f"[SUCCESS] Exported {total_scenarios} scenarios ({total_frames} total frames) to '{golden_path}'"
    )


if __name__ == "__main__":
    main()
