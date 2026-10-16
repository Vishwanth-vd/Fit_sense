# FitSense AI (Push-up)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Flutter](https://img.shields.io/badge/flutter-stable-02569B.svg)](https://flutter.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **IMPORTANT NON-MEDICAL DISCLAIMER**  
> **FitSense AI is a personal workout feedback and fitness tracking application, NOT a medical device.**  
> It does not diagnose, treat, prevent, or rehabilitate any physical ailments or musculoskeletal injuries. All cues, form flags, and metrics provided by the app are for educational and athletic workout feedback only and should never replace certified medical or fitness coaching.

---

## 1. Project Overview

**FitSense AI (Push-up)** is an intelligent mobile workout assistant that leverages on-device computer vision to:
1. **Detect & Count Push-ups in Real Time:** Operates directly on the smartphone camera stream using Google MediaPipe Pose Landmarker.
2. **Assess Exercise Form (Biomechanical Rules):** Analyzes elbow flexion, body alignment, and hip sag/pike using a deterministic finite state machine (FSM).
3. **Personalized Dynamic Baseline:** Calibrates against the user's initial 5 non-low-confidence reps within a session, alerting only when statistically significant deviation occurs ($|z| > 2$ across 3 consecutive reps).
4. **Spoken Audio Feedback:** Delivers timely, rate-limited natural voice cues via text-to-speech without disrupting the workout rhythm.
5. **Privacy by Design:** **Zero video or images are stored or uploaded.** All frame inference happens locally in volatile memory; only derived mathematical metrics and rep counts are persisted or synced.

---

## 2. Inspiration & Acknowledgments

- **Reference Project:** [FormFit](https://github.com/akheelnazim/FormFit) by **Akheel Nazim** (developed for the Benefit Advanced AI Hackathon 2024, University of Bahrain).
- **Credit & Policy:** FormFit is cloned read-only into `./reference/FormFit` to analyze real-world MediaPipe capture and study pose classification workflows. FitSense AI does not copy FormFit code; all algorithms, state machines, Flutter components, and FastAPI microservices in FitSense AI are original implementations. We gratefully credit Akheel Nazim for inspiring this research direction.

---

## 3. Technology Stack

- **Mobile Client:**
  - **Framework:** Flutter (stable channel, Dart with sound null safety, Android-first).
  - **On-Device Pose Estimation:** Google MediaPipe Pose Landmarker via pinned plugin (`flutter_mp_pose_landmarker: 0.1.9`).
  - **Local Persistence:** SQLite via `sqflite` (offline-first architecture).
  - **Speech Synthesis:** `flutter_tts` (rate-limited, on-device audio cues).
  - **Visualization:** `fl_chart` (session telemetry, angle profiles, tempo).
- **Backend Service:**
  - **Language & Runtime:** Python 3.11+.
  - **API Framework:** FastAPI with Pydantic v2 schemas and validation.
  - **Database:** MongoDB Atlas (free tier) accessed exclusively via HTTPS from FastAPI (the mobile app never connects directly to MongoDB).
  - **Security:** OAuth2 Password Bearer flow issuing HS256 JWT tokens; password hashing with Argon2 or Bcrypt; rate-limited auth endpoints; strict CORS.
- **Offline ML (Optional Phase P7):** Python, pandas, scikit-learn (participant-wise cross-validation).

---

## 4. Repository Layout

```text
fitsense/
├── prototype/          # Python reference implementation, video/webcam runner & unit tests
│   ├── analyzer/       # Biomechanical math & push-up FSM state machine
│   ├── config/         # Centralized algorithm thresholds (no hard-coded constants)
│   ├── tests/          # Synthetic test suites (clean reps, partial reps, jitter, frame exits)
│   └── vectors/        # Exported golden JSON test vectors for Dart parity testing
├── app/                # Flutter mobile application (Android-first)
│   ├── lib/            # UI, camera preview, skeleton overlay, analyzer port, SQLite DB
│   └── test/           # Dart parity unit tests matching Python golden vectors
├── backend/            # FastAPI backend service
│   ├── app/            # Routers, Pydantic v2 schemas, MongoDB Atlas client, JWT auth
│   └── tests/          # Backend API endpoint test suite
├── ml/                 # Offline feature extraction & training scripts (Phase P7)
├── docs/               # Project documentation
│   ├── decisions.md    # Architectural Decision Records (ADRs) & package evaluations
│   ├── architecture.md # Comprehensive system architecture & pipeline specification
│   ├── privacy.md      # Data governance, zero-video retention guarantee & user consent
│   └── demo-script.md  # Viva & live demonstration script
├── reference/          # Read-only external reference repositories
│   └── FormFit/        # Cloned reference repo (FormFit by Akheel Nazim)
├── .env.example        # Environment variable templates and security warnings
├── .gitignore          # Multi-stack git exclusions
├── pyproject.toml      # Python linter (Ruff), formatter (Black), and test (pytest) config
├── analysis_options.yaml # Flutter/Dart strict analysis options
└── README.md           # Master project documentation
```

---

## 5. Algorithm Specification

All thresholds are centralized in a single configuration class (`PushUpConfig`), shared identically in Python and Dart:

1. **Dominant Side Selection:** Compares left-side `(11, 13, 15, 23, 25, 27)` vs right-side `(12, 14, 16, 24, 26, 28)` average visibility; chooses the side with higher confidence.
2. **Quality & Smoothing:** Landmarks with visibility $< 0.5$ are filtered out. Positions are smoothed using a moving average window ($N = 5$ frames).
3. **Per-Frame Features:**
   - **Elbow Angle:** $\angle(\text{Shoulder}, \text{Elbow}, \text{Wrist})$.
   - **Body-Line Angle:** $\angle(\text{Shoulder}, \text{Hip}, \text{Ankle})$.
   - **Normalized Hip Deviation:** Perpendicular signed distance of hip from shoulder-ankle line, normalized by torso length.
   - **Body Orientation Gate:** Shoulder-ankle line must be within $35^\circ$ of horizontal (otherwise the user is not in push-up position).
4. **Rep State Machine:**
   - Flow: `UP` $\to$ `LOWERING` $\to$ `DOWN` $\to$ `RAISING` $\to$ `UP`.
   - Hysteresis thresholds: `UP` at elbow $\ge 155^\circ$, `DOWN` at elbow $\le 95^\circ$.
   - Minimum duration: $\ge 0.8\text{ s}$ per rep. Partial repetitions (failing to reach $\le 95^\circ$) are flagged as `partial_range`.
5. **Personal Baseline:** First 5 non-low-confidence reps compute $\mu$ and $\sigma$. Flags are raised only when $|z| > 2$ across 3 consecutive reps.
6. **Voice Cues:** Rate-limited to at most one spoken cue every 5 seconds.

---

## 6. Backend API Endpoints

All requests validate against strict Pydantic v2 models. The user ID is always extracted from the verified JWT token:

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Create a new user account with consent timestamp | No (Rate-limited) |
| `POST` | `/auth/login` | Authenticate user and issue JWT access token | No (Rate-limited) |
| `POST` | `/sessions` | Upload and persist completed workout session | Yes (Bearer JWT) |
| `GET` | `/sessions` | Retrieve own historical sessions (paginated) | Yes (Bearer JWT) |
| `GET` | `/baseline` | Retrieve current user personal baseline | Yes (Bearer JWT) |
| `PUT` | `/baseline` | Update or reset user personal baseline | Yes (Bearer JWT) |
| `DELETE`| `/me` | Complete data erasure (user, sessions, baselines) | Yes (Bearer JWT) |

---

## 7. Project Implementation Phases

- [x] **P0: Project Scaffolding & Setup** — Repo layout, docs, .gitignore, .env.example, lint configs, reference relocation.
- [ ] **P1: Python Prototype & Golden Vectors** — Push-up analyzer, synthetic test generator, parity vector export.
- [ ] **P2: Flutter Camera & Pose Tracking** — Android camera preview, MediaPipe integration, skeleton overlay, FPS counter.
- [ ] **P3: Dart Analyzer Parity** — Port analyzer to Dart; pass identical test vectors with exact parity.
- [ ] **P4: Workout UI & Audio Guidance** — Setup screen, 2-meter readable live UI, wakelock, rate-limited spoken voice cues.
- [ ] **P5: SQLite Persistence & Analytics** — Offline history, fl_chart visualizations, baseline analytics.
- [ ] **P6: FastAPI Backend & Cloud Sync** — MongoDB Atlas integration, JWT auth, offline-first sync queue, account deletion.
- [ ] **P7: Offline ML & Feature Extraction (Optional)** — Scikit-learn Random Forest benchmarking with participant-wise split.
- [ ] **P8: Final Auditing, Documentation & Demo Prep** — Verification of all test suites, honest limitations, viva demo rehearsal.
