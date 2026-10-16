"""FitSense AI - Video File Runner.

Runs PushUpAnalyzer over pre-recorded video files (.mp4, .avi) using MediaPipe Pose.
Outputs per-frame biomechanical statistics and completed repetition logs.
"""

import argparse
import sys
import time

import cv2

from prototype.analyzer import PushUpAnalyzer
from prototype.config import PushUpConfig
from prototype.models import Landmark

try:
    import mediapipe as mp

    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False


def extract_landmarks_from_mediapipe(results) -> dict[int, Landmark]:
    """Convert MediaPipe PoseLandmarker output into a dict of Landmark models."""
    landmarks_dict: dict[int, Landmark] = {}
    if not results or not results.pose_landmarks:
        return landmarks_dict

    for idx, lm in enumerate(results.pose_landmarks.landmark):
        landmarks_dict[idx] = Landmark(
            x=lm.x,
            y=lm.y,
            z=lm.z,
            visibility=getattr(lm, "visibility", 1.0),
            presence=getattr(lm, "presence", 1.0),
        )
    return landmarks_dict


def run_video(
    video_path: str,
    output_path: str | None = None,
    show_preview: bool = False,
) -> int:
    """Analyze a push-up video file and log repetition metrics."""
    if not HAS_MEDIAPIPE:
        print("[ERROR] MediaPipe is required to run the video analyzer.")
        return 1

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Unable to open video file: {video_path}")
        return 1

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(
        f"[INFO] Processing '{video_path}' | {width}x{height} @ {fps:.1f} FPS | {total_frames} frames"
    )

    writer = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    mp_draw = mp.solutions.drawing_utils

    analyzer = PushUpAnalyzer(config=PushUpConfig())
    frame_idx = 0
    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_s = frame_idx / fps
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        landmarks = extract_landmarks_from_mediapipe(results)
        features, completed_rep, spoken_cue = analyzer.process_frame(
            landmarks, timestamp_s
        )

        if completed_rep:
            clean_str = (
                "CLEAN" if completed_rep.is_clean else f"FLAGS={completed_rep.flags}"
            )
            print(
                f"[REP COMPLETED] #{completed_rep.n} | Duration: {completed_rep.duration_s:.2f}s | "
                f"Min Elbow: {completed_rep.min_elbow_angle:.1f}° | {clean_str}"
            )
        if spoken_cue:
            print(f'  >>> [VOICE CUE]: "{spoken_cue}"')

        # Visual overlay
        if writer or show_preview:
            if results.pose_landmarks:
                mp_draw.draw_landmarks(
                    frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
                )

            # Draw HUD
            hud_text = f"Reps: {analyzer.clean_rep_count} / {analyzer.rep_count} | State: {analyzer.state.value}"
            cv2.putText(
                frame, hud_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2
            )

            if features:
                angle_text = f"Elbow: {features.elbow_angle:.1f}° | Body: {features.body_line_angle:.1f}°"
                cv2.putText(
                    frame,
                    angle_text,
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            if spoken_cue:
                cv2.putText(
                    frame,
                    f"CUE: {spoken_cue}",
                    (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 165, 255),
                    2,
                )

            if writer:
                writer.write(frame)
            if show_preview:
                cv2.imshow("FitSense AI - Video Runner", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        frame_idx += 1

    elapsed = time.time() - start_time
    proc_fps = frame_idx / elapsed if elapsed > 0 else 0
    print(
        f"\n[SUMMARY] Processed {frame_idx} frames in {elapsed:.2f}s ({proc_fps:.1f} FPS)"
    )
    print(
        f"[SUMMARY] Total Reps Detected: {analyzer.rep_count} | Clean: {analyzer.clean_rep_count}"
    )

    cap.release()
    if writer:
        writer.release()
    if show_preview:
        cv2.destroyAllWindows()
    pose.close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FitSense AI Video File Runner")
    parser.add_argument("video", type=str, help="Path to input video file")
    parser.add_argument(
        "--output", type=str, default=None, help="Path to output annotated video"
    )
    parser.add_argument(
        "--preview", action="store_true", help="Display live rendering preview"
    )
    args = parser.parse_args()

    sys.exit(run_video(args.video, args.output, args.preview))
