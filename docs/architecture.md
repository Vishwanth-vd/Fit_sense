# System Architecture - FitSense AI (Push-up)

## 1. System Overview

**FitSense AI** is an on-device, real-time push-up tracking and form assessment mobile application. It captures device camera video, estimates 33-point body pose landmarks using Google MediaPipe Pose Landmarker on-device, computes geometric biomechanical angles, counts valid/partial repetitions via a finite state machine, evaluates personal baseline deviations, and provides spoken audio cues.

> **CRITICAL DISCLAIMER:**  
> FitSense AI is an educational fitness tracking and workout feedback tool. **It is NOT a medical device** and does not make medical, clinical, therapeutic, or injury-prevention claims.

```
+-----------------------------------------------------------------------------------+
|                                 MOBILE CLIENT (Flutter)                           |
|                                                                                   |
|  +--------------------+     +------------------------+     +-------------------+  |
|  | Android CameraX    | --> | MediaPipe Pose         | --> | PushUpAnalyzer    |  |
|  | Video Stream       |     | Landmarker (On-Device) |     | (Pure Dart Logic) |  |
|  +--------------------+     +------------------------+     +-------------------+  |
|                                                                      |            |
|       +--------------------------------------------------------------+            |
|       v                                                              v            |
|  +---------------------+                                    +------------------+  |
|  | UI Overlay & Voice  |                                    | Local SQLite DB  |  |
|  | (flutter_tts, FPS)  |                                    | (Offline First)  |  |
|  +---------------------+                                    +------------------+  |
|                                                                      |            |
+----------------------------------------------------------------------|------------+
                                                                       | HTTPS Sync
                                                                       v (Derived numbers only)
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND (Python 3.11)                      |
|                                                                                   |
|  +----------------------+      +----------------------+     +------------------+  |
|  | JWT Auth Middleware  | ---> | Session / Baseline   | --> | MongoDB Atlas    |  |
|  | (Rate Limiting)      |      | Pydantic v2 Models   |     | (Encrypted TLS)  |  |
|  +----------------------+      +----------------------+     +------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. On-Device Repetition & Form Analysis Pipeline

The analyzer logic is designed to be 100% deterministic and mathematically identical between the Python reference prototype (`prototype/`) and the Flutter Dart implementation (`app/`).

### Step 1: Landmark Extraction & Best-Side Selection
- 33 landmarks from MediaPipe Pose Landmarker.
- FitSense AI tracks single-person side view.
- Compares average visibility of left-side joints `(11, 13, 15, 23, 25, 27)` vs right-side joints `(12, 14, 16, 24, 26, 28)`.
- Selects the dominant side with higher visibility for frame analysis.

### Step 2: Quality Filtering & Smoothing
- Any landmark with confidence/visibility $< 0.5$ is marked invalid.
- Landmark coordinates are smoothed with a sliding moving average window (default $N = 5$ frames) to suppress high-frequency camera noise and coordinate jitter.

### Step 3: Biomechanical Feature Extraction (Per Frame)
1. **Body Orientation Check:**
   - Angle between shoulder-ankle line and horizontal ground plane.
   - Must be $\le 35^\circ$ from horizontal. If the person is standing, sitting, or kneeling upright, no push-up reps can be counted.
2. **Elbow Joint Angle:**
   - 3-point planar angle at the elbow: $\angle(\text{Shoulder}, \text{Elbow}, \text{Wrist})$.
3. **Body-Line Alignment Angle:**
   - Angle between shoulder, hip, and ankle: $\angle(\text{Shoulder}, \text{Hip}, \text{Ankle})$.
4. **Normalized Hip Deviation:**
   - Perpendicular signed distance of the hip joint from the segment connecting shoulder and ankle, divided by torso length (shoulder-to-hip distance).
   - Positive deviation indicates hips piked upward; negative deviation indicates sagging hips.

### Step 4: Finite State Machine (FSM)
- States: `UP` $\to$ `LOWERING` $\to$ `DOWN` $\to$ `RAISING` $\to$ `UP`.
- **Hysteresis Thresholds:**
  - `UP` state: $\text{Elbow Angle} \ge 155^\circ$.
  - `DOWN` state: $\text{Elbow Angle} \le 95^\circ$.
- **Rep Completion Criteria:**
  - Repetition completes when returning to `UP` state ($\ge 155^\circ$).
  - Minimum rep duration threshold: $\ge 0.8\text{ s}$ to reject false-positive twitching.
  - If a rep cycle starts from `UP`, dips, and returns to `UP` without reaching `DOWN` ($\le 95^\circ$), it is flagged as `partial_range` and not counted as a clean rep.

### Step 5: Metric Aggregation & Low-Confidence Rules
For each completed repetition:
- Rep duration ($s$), down/up tempo ratio.
- Minimum elbow angle achieved ($^\circ$).
- Mean body-line angle ($^\circ$).
- Peak hip deviation (sag/pike).
- Mean landmark tracking visibility.
- **Rule:** If mean landmark visibility $< 0.6$, the rep is flagged `low_confidence`. It is excluded from the user's personal baseline calculations and does not trigger harsh form critique.

### Step 6: Personal Baseline Calibration
- The first 5 non-low-confidence repetitions of a session form the user's dynamic personal baseline:
  $$\mu = \text{mean}(x), \quad \sigma = \text{std}(x)$$
- For subsequent repetitions:
  $$z = \frac{x - \mu}{\sigma + \epsilon}$$
- An anomaly flag is raised only if $|z| > 2.0$ across $3$ consecutive repetitions, avoiding jittery one-off false alarms.

### Step 7: Voice Guidance Rate Limiting
- Natural spoken feedback via TTS (e.g., "Go a little lower", "Keep your hips up").
- Hard rate limit: **At most one spoken audio cue every 5 seconds**.

---

## 3. Data Contracts & Persistence

### 3.1 Privacy by Design
- **Strictly derived numerical features:** Only timestamps, joint angles, counts, and flags are stored.
- **NO camera frames, video clips, or photos are ever written to disk or sent over the network.**

### 3.2 Unified Data Model (SQLite & MongoDB)
- **`users`:** `user_id`, `email`, `password_hash`, `created_at`, `consent_at`.
- **`workout_sessions`:** `id`, `user_id`, `exercise_type="pushup"`, `started_at`, `completed_at`, `reps_detected`, `tracking_quality`, `synced` (device only), `reps[]`.
- **`user_baselines`:** `user_id`, `exercise_type="pushup"`, `feature_stats`, `updated_at`.

---

## 4. Network & Sync Architecture
- Offline-first: The Flutter app operates fully autonomously without network connectivity.
- Sync worker checks connectivity, pushes pending sessions to `POST /sessions`, and marks records `synced = true` upon HTTP 201 response.
- Retry queue employs exponential backoff with jitter.
