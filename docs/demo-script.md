# College Mini-Project Demo Script - FitSense AI (Push-up)

This script provides a structured 5-to-7 minute walkthrough for presenting and demonstrating **FitSense AI** during project evaluations or live viva sessions.

---

## Pre-Demo Checklist & Setup

- [ ] Phone charged (or connected to power) with Android developer mode enabled.
- [ ] Fast-response local Wi-Fi or USB reverse tethering active.
- [ ] FastAPI backend running (`uvicorn backend.main:app --host 0.0.0.0 --port 8000`).
- [ ] Clear floor space with unobstructed side view (~2.0 to 2.5 meters distance between camera and workout mat).
- [ ] Good ambient lighting (avoid direct backlighting behind the user).
- [ ] Phone volume set to 75% for clear Text-to-Speech audio cues.

---

## Step-by-Step Presentation Script

### 1. Introduction & Problem Statement (1 min)
- **Speaker:** "Good morning/afternoon. Today I am presenting **FitSense AI**, an on-device computer vision mobile application designed for real-time push-up counting, form assessment, and personalized baseline feedback."
- **Key Highlight:** "Unlike cloud-dependent fitness apps that upload video streams, FitSense AI processes 100% of the video frames on the phone using Google MediaPipe Pose Landmarker. Only derived biomechanical angles and timestamps are stored—zero video or images ever leave the device. Additionally, this is an exercise feedback tool, not a medical device."

### 2. Camera Setup & Pre-Flight Calibration (1 min)
- Open the FitSense AI app on the phone.
- Navigate to **"Start Push-up Session"**.
- Position the camera on the floor or a low stand perpendicular to the exercise mat (side view).
- **Show the Evaluator:**
  - The live setup screen checks 3 conditions before unlocking:
    1. Full body detected (head, shoulders, hips, knees, ankles in frame).
    2. Body orientation side-on.
    3. Landmark visibility score $\ge 0.6$.
  - The **"Start Workout"** button dynamically illuminates from disabled grey to active emerald green once conditions are satisfied.

### 3. Live Workout & Spoken Audio Feedback (2 mins)
- Press **"Start Workout"** (3-second countdown initiates).
- Assume horizontal push-up plank position.
- **Show the Evaluator on the large screen / phone:**
  - Real-time skeleton overlay with joint tracking.
  - Live FPS counter showing measured frame rate ($\ge 20\text{ FPS}$).
  - Real-time elbow angle meter with state hysteresis (`UP` $\ge 155^\circ \to$ `DOWN` $\le 95^\circ$).
- **Demonstration Repetitions:**
  - **Rep 1 to 3 (Clean Reps):** Full depth push-ups. App speaks: *"One"*, *"Two"*, *"Three"*.
  - **Rep 4 (Partial Range):** Dip only to $115^\circ$ and return. App flags `partial_range` and speaks: *"Go a little lower"*.
  - **Rep 5 (Hips Sagging):** Sag hips down. App flags `hips_sagging` and speaks: *"Keep your hips up"*.
  - **Rep 6 (Fast Jitter):** Pump rapidly $< 0.8\text{ s}$. App enforces minimum duration filter and flags `too_fast`.
  - **Note Rate Limiting:** Show that speech cues respect the 5-second cooldown to avoid auditory clutter.

### 4. Post-Workout Summary & Personal Baseline (1.5 mins)
- Tap **"Finish Workout"**.
- The app transitions to the **Session Summary Report**:
  - Total reps detected vs. clean reps.
  - Breakdown of form flags (sagging, piked, partial depth).
  - Interactive **fl_chart** showing elbow angle trajectory, down/up tempo, and duration across reps.
  - **Personal Baseline:** Explain how the first 5 non-low-confidence reps calibrated the session baseline, and subsequent reps were compared using normalized z-scores ($|z| > 2$ on 3 consecutive reps).

### 5. Offline-First SQLite & Cloud Sync Verification (1 min)
- Show the **Workout History** tab: Session was immediately written to local SQLite database.
- Demonstrate cloud sync with FastAPI backend:
  - App sends derived statistics via `POST /sessions`.
  - Status updates to `synced: true`.
  - Show FastAPI backend terminal log confirming receipt of session payload.
- **Privacy Verification:** Inspect the MongoDB Atlas record or FastAPI response to show evaluators that only numerical metrics and timestamps exist in the database—zero pixels.

### 6. Data Erasure & Conclusion (30 sec)
- Show the **"Delete My Account & Data"** option (`DELETE /me`).
- Summarize accomplishments: On-device ML, reproducible Python/Dart parity, strict privacy, and reliable workout telemetry.
- Open the floor for questions.
