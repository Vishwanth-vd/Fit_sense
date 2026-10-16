"""FitSense AI - Live Webcam Runner.

Executes real-time PushUpAnalyzer on live camera video feed:
- Live FPS calculation and rendering.
- Setup pre-flight check (full body visible, side-on orientation, confidence).
- Visual HUD with joint angles, state machine transitions, and voice cues.
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


def extract_landmarks(results) -> dict[int, Landmark]:
    """Convert MediaPipe results to Landmark objects."""
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


def run_webcam(camera_index: int = 0) -> int:
    """Run real-time webcam push-up session."""
    if not HAS_MEDIAPIPE:
        print("[ERROR] MediaPipe is required to run live webcam analysis.")
        return 1

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Could not access webcam at index {camera_index}.")
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    mp_draw = mp.solutions.drawing_utils

    analyzer = PushUpAnalyzer(config=PushUpConfig())

    prev_frame_time = time.time()
    fps_history = []
    fps_display = 0.0

    print("[INFO] Starting webcam runner. Press 'q' to quit, 'r' to reset session.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        dt = now - prev_frame_time
        prev_frame_time = now

        if dt > 0:
            current_fps = 1.0 / dt
            fps_history.append(current_fps)
            if len(fps_history) > 15:
                fps_history.pop(0)
            fps_display = sum(fps_history) / len(fps_history)

        # Process frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)
        landmarks = extract_landmarks(results)

        features, completed_rep, spoken_cue = analyzer.process_frame(landmarks, now)

        # Draw skeleton
        if results.pose_landmarks:
            mp_draw.draw_landmarks(
                frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
            )

        # Draw HUD Box
        h, w, _ = frame.shape
        cv2.rectangle(frame, (10, 10), (420, 200), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 10), (420, 200), (70, 70, 70), 2)

        # Stats Overlay
        cv2.putText(
            frame,
            f"FitSense AI | FPS: {fps_display:.1f}",
            (25, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 200),
            2,
        )

        rep_text = (
            f"Reps: {analyzer.clean_rep_count} clean / {analyzer.rep_count} total"
        )
        cv2.putText(
            frame,
            rep_text,
            (25, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2,
        )

        state_color = (0, 255, 0) if analyzer.state.value == "UP" else (0, 165, 255)
        cv2.putText(
            frame,
            f"State: {analyzer.state.value}",
            (25, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            state_color,
            2,
        )

        if features:
            cv2.putText(
                frame,
                f"Elbow: {features.elbow_angle:.1f} deg | Torso: {features.body_line_angle:.1f} deg",
                (25, 145),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (200, 200, 200),
                1,
            )
            side_text = f"Side: {features.dominant_side.value} | Hip Dev: {features.hip_deviation:.3f}"
            cv2.putText(
                frame,
                side_text,
                (25, 175),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (200, 200, 200),
                1,
            )

        # Large Voice Cue Banner
        if spoken_cue:
            cv2.putText(
                frame,
                f"CUE: {spoken_cue}",
                (w // 2 - 200, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 215, 255),
                3,
            )

        cv2.imshow("FitSense AI - Live Push-up Tracker", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            analyzer.reset()
            print("[INFO] Session reset.")

    cap.release()
    cv2.destroyAllWindows()
    pose.close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FitSense AI Live Webcam Runner")
    parser.add_argument("--camera", type=int, default=0, help="Webcam device index")
    args = parser.parse_args()

    sys.exit(run_webcam(args.camera))
