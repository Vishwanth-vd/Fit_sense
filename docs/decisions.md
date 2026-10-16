# Architectural & Technical Decision Records (ADR) - FitSense AI

This document logs all key architectural and technology decisions for **FitSense AI (Push-up)**, including package evaluations, rationale, trade-offs, and pinned versions.

---

## ADR-001: MediaPipe Pose Landmarker Flutter Plugin Selection

### Context
FitSense AI requires real-time, on-device 33-point pose landmark tracking on Android at sufficient frame rates (>= 20 FPS) with side-view visibility detection for push-up tracking. The user algorithm specification requires:
- Raw access to 33 body landmarks (specifically shoulders 11/12, elbows 13/14, wrists 15/16, hips 23/24, knees 25/26, ankles 27/28) with visibility and presence confidence scores.
- A custom, pure-Dart analyzer that achieves bit-level / algorithmic parity with the Python reference analyzer.
- Direct live camera streaming with minimal latency.

### Options Evaluated on pub.dev

#### 1. `flutter_mp_pose_landmarker` (Current version: `0.1.9`)
- **Strengths:**
  - Lightweight, focused plugin specifically dedicated to Google's MediaPipe Pose Landmarker.
  - Native Android CameraX integration streaming landmark data efficiently via `EventChannel`.
  - Exposes clean, raw 33 landmark points `(x, y, z, visibility, presence)` directly without bundling opinionated or unneeded high-level fitness heuristics that would interfere with our custom algorithm specification.
  - Stable Android support with straightforward permissions and native pipeline.
- **Weaknesses:**
  - Does not supply pre-built fitness analytics (which is actually an advantage here, as our specification dictates our own exact custom state machine and parity with Python prototype).

#### 2. `vision_ai_pose` (Current version: `0.1.0`, dependent on `vision_ai: ^0.4.0`)
- **Strengths:**
  - Part of the broader `vision_ai` modular ecosystem.
  - Provides pre-bundled `.task` assets and high-level wrappers.
- **Weaknesses:**
  - Complex multi-package dependency tree (`vision_ai`, `vision_ai_pose`, `vision_ai_flutter`).
  - Bundles its own built-in angle calculators and posture tools which duplicate or clash with our strict custom parity requirements.
  - Requires disabling Android R8 shrinking completely, which impacts production bundle sizing.
  - Relatively newer release (`0.1.0`), resulting in faster-shifting internal APIs.

### Decision
**Select and pin `flutter_mp_pose_landmarker: 0.1.9`** (with fallback compatibility for `vision_ai_pose` if specific hardware demands).
- Provides exact raw landmarks needed by our pure Dart `PushUpAnalyzer`.
- Clean CameraX integration on Android.
- Enables straightforward unit testing of the Dart analyzer with synthetic JSON test vectors independent of the camera plugin.

---

## ADR-002: Local Storage Engine (SQLite via sqflite vs. drift)

### Context
The app must persist workout sessions, reps, tracking quality metrics, and local user baselines offline on the device. Sync status must be maintained locally without using Realm or Atlas Device Sync.

### Decision
**Select `sqflite` (pinned: `^2.3.3`)**
- Direct control over relational tables and schema migration.
- Lightweight, predictable performance on Android.
- Mirrors the MongoDB collection document structure seamlessly without heavy ORM codegen overhead.

---

## ADR-003: Voice Feedback Engine

### Context
Real-time spoken feedback ("Go a little lower", "Keep your hips up") during workouts, rate-limited to at most one cue per 5 seconds.

### Decision
**Select `flutter_tts` (pinned: `^4.2.2`)**
- Standard, robust Flutter text-to-speech solution on Android.
- Zero network dependency (uses Android native TTS engine locally).
- Low latency, non-blocking audio output.

---

## ADR-004: Data Visualization & Charting

### Context
Visualizing rep duration, joint angles, down/up tempo, and baseline deviation across historical workout sessions.

### Decision
**Select `fl_chart` (pinned: `^0.70.2`)**
- The leading Flutter charting library with high-performance canvas rendering.
- Fully supports custom styling, responsive tooltips, line charts, and bar charts.

---

## ADR-005: Backend Architecture & Auth

### Context
FastAPI service on Python 3.11 with MongoDB Atlas, user registration/login, JWT authentication, rate limiting, and GDPR-compliant data deletion.

### Decision
- **Framework:** FastAPI with Pydantic v2 for strict request/response data contracts.
- **Database Driver:** `motor` / `pymongo` connecting securely over HTTPS/TLS to MongoDB Atlas.
- **Authentication:** OAuth2 password flow issuing signed HS256 JWT tokens with user ID claim.
- **Password Hashing:** `argon2-cffi` (recommended by OWASP) or `bcrypt`.
- **CORS & Rate Limiting:** Locked-down CORS middleware and `slowapi` rate limiter on auth routes.
- **Data Minimization:** No video or image frames are ever accepted, processed, or stored by the backend. Only derived numerical statistics and rep counts.
