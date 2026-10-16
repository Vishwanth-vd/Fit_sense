# Privacy & Data Governance - FitSense AI

## 1. Core Privacy Philosophy: On-Device Processing by Design

FitSense AI is designed with strict **Data Minimization** and **Privacy by Design** principles in accordance with modern privacy standards (such as GDPR and CCPA guidelines).

---

## 2. Strict Zero-Image Retention Guarantee

1. **No Raw Video or Photo Storage:**  
   The device camera stream is processed strictly in volatile RAM by the on-device MediaPipe Pose Landmarker pipeline.
2. **Immediate Frame Discard:**  
   Once the 33 3D/2D landmark coordinates are extracted from a frame, the video buffer is instantly released and discarded. Raw pixels never touch the filesystem, cache, or external storage.
3. **No Visual Media Transmission:**  
   The application **NEVER** uploads, transmits, or streams photos, video recordings, or facial images to any remote server or cloud service.

---

## 3. What Data Is Collected and Stored

FitSense AI collects and stores **strictly derived, non-personally-identifying biomechanical telemetry**:

| Data Element | Purpose | Stored Locally | Synced to Cloud |
| :--- | :--- | :--- | :--- |
| **Account Email & Password Hash** | Authentication & user scoping | Optional (local token) | Yes (Argon2 hashed) |
| **User Consent Timestamp** | Verifiable privacy terms acceptance | Yes | Yes |
| **Workout Timestamps** | Session start and finish times | Yes | Yes |
| **Repetition Counts** | Total clean and partial repetitions | Yes | Yes |
| **Joint Angles & Deviation Metrics** | Minimum elbow angle, torso alignment, hip deviation | Yes | Yes |
| **Landmark Confidence / Visibility** | Ensuring baseline accuracy and data quality | Yes | Yes |
| **Personal Baseline Statistics** | Mean and standard deviation of first 5 reps | Yes | Yes |
| **Camera Video / Image Frames** | Temporary input for pose estimation | **NEVER** | **NEVER** |

---

## 4. User Consent & Rights

### 4.1 Explicit Informed Consent
Before camera tracking or account synchronization is activated, the user must explicitly accept the privacy terms. The exact timestamp is recorded as `consent_at`.

### 4.2 Right to Erasure (Account & Data Deletion)
Users have full sovereignty over their data:
- **`DELETE /me` Endpoint:** Authenticated API request that permanently deletes the user's account, all associated workout sessions, and historical baselines from MongoDB Atlas.
- **Local App Clear Data:** The user can clear the local SQLite database at any time from the app settings, purging all offline history.

---

## 5. Non-Medical Purpose & Scope Disclaimer

> **IMPORTANT NOTICE:**  
> FitSense AI is developed as an educational computer science mini-project and fitness workout feedback assistant.  
> - It is **NOT** a certified medical device, orthopedic diagnostic tool, or clinical physical therapy instrument.  
> - It does not provide medical advice, diagnosis, treatment, or injury-prevention guarantees.  
> - Form feedback cues are based on general athletic workout guidelines and must not supersede advice from certified medical or physical fitness professionals.
