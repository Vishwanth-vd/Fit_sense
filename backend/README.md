# FitSense AI - FastAPI Backend Service

This directory contains the Python 3.11 FastAPI backend service for FitSense AI.

## Highlights
- **Framework:** FastAPI with Pydantic v2 schemas.
- **Database:** MongoDB Atlas (free tier) via PyMongo/Motor over encrypted TLS.
- **Authentication:** OAuth2 JWT tokens with Argon2/Bcrypt password hashing.
- **Strict Data Minimization:** Stores only derived telemetry numbers, counts, and baseline statistics. Video and images are NEVER accepted.
- **Endpoints:**
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /sessions` (Ingest workout session)
  - `GET /sessions` (Own sessions, paginated)
  - `GET /baseline` & `PUT /baseline`
  - `DELETE /me` (Full data deletion / right to erasure)
