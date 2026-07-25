# LeakLens AI — Production Deployment Guide

This document explains how to deploy LeakLens AI to production (backend on Render, frontend on Vercel) and verify the deployment.

---

## Summary
- Backend: FastAPI application (backend/) — deploy to Render (recommended) or other provider.
- Frontend: Next.js (frontend/) — deploy to Vercel.
- Database: PostgreSQL (managed) — Render PostgreSQL or other provider.

---

## Required environment variables (backend)
- DATABASE_URL — e.g. `postgresql+psycopg2://<user>:<pass>@<host>:5432/<db>`
- ENVIRONMENT=production
- SECRET_KEY — 32+ char secret
- ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=10080
- UPLOAD_DIR — e.g. `/data/uploads`
- CHROMA_PATH — e.g. `/data/chroma`
- BACKEND_CORS_ORIGINS — JSON array or comma-separated list with frontend origin(s), e.g. `["https://my-frontend.vercel.app"]`

## Required environment variables (frontend / Vercel)
- NEXT_PUBLIC_API_URL — e.g. `https://<your-backend-domain>/api/v1`

---

## Backend build & run (local test)
1. Create virtualenv and install deps:

```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Ensure DATABASE_URL is set (pointing to production or test DB)

```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/leaklens"
```

3. Run migrations

```bash
alembic upgrade head
```

4. Start server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health: GET /health

---

## Frontend build & run (local test)

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run build
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run start
```

---

## Deploy Backend to Render (recommended)
1. Create a new Web Service on Render and connect your repository.
2. In "Root Directory" set `backend`.
3. Environment:
   - Set the environment variables listed above (DATABASE_URL, SECRET_KEY, BACKEND_CORS_ORIGINS...).
4. Build & Start Command (Render):

```
# Build command (Render will detect Python):
# Use a release command to run migrations before start
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

5. Use Render PostgreSQL for DATABASE_URL (create a database via Render dashboard and copy the connection string into DATABASE_URL).

---

## Deploy Frontend to Vercel
1. Import the repo into Vercel.
2. Set root directory to `frontend`.
3. Set environment variable `NEXT_PUBLIC_API_URL` to `https://<your-backend-domain>/api/v1`.
4. Set build command: `npm run build` and output directory left default (Next.js).
5. Deploy.

---

## Post-deploy verification
1. Health check: GET `https://<backend>/health` => {status: ok}
2. Register a new user via UI or `POST /api/v1/auth/register`.
3. Login to get token; frontend should persist token and include it in Authorization header.
4. Upload a sample CSV via UI; status should be `Processed` and transactions saved.
5. Subscriptions should be detected; recommendations generated; analytics should return non-zero values.
6. Confirm charts and downloads work.

---

## Troubleshooting
- If `pydantic-core` fails to install in Python 3.14: use Python 3.11 or 3.12.
- If migrations fail: ensure DATABASE_URL points to the correct database and the DB user has migration privileges.
- If CORS errors: ensure BACKEND_CORS_ORIGINS includes exact frontend origin (protocol + host).

---

## Notes
- The app expects production DB to be PostgreSQL for multi-instance reliability.
- Avoid using SQLite in production when multiple instances/containers are used.

