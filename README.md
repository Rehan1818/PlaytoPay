# Playto Payout Engine

Minimal payout engine for merchants receiving international payments and withdrawing INR balances.

## Stack

- Backend: Django + DRF + PostgreSQL
- Background jobs: Huey + Redis
- Frontend: React + Tailwind (Vite)

## Project Structure

- `backend/` Django API and payout engine
- `frontend/` React dashboard

## Backend Setup

1. Create and activate virtualenv.
2. Install dependencies:
   - `pip install -r backend/requirements.txt`
3. Configure env vars (or defaults in settings):
   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
   - `REDIS_URL`
4. Run migrations:
   - `python backend/manage.py makemigrations`
   - `python backend/manage.py migrate`
5. Seed test data:
   - `python backend/manage.py seed_data`
6. Start API:
   - `python backend/manage.py runserver`
7. Start worker (separate shell):
   - `python backend/manage.py run_huey`

## Frontend Setup

1. Install dependencies:
   - `cd frontend && npm install`
2. Start dev server:
   - `npm run dev`
3. Open provided Vite URL.

## Key Endpoints

- `POST /api/v1/payouts` (headers: `X-Merchant-Id`, `Idempotency-Key`)
- `GET /api/v1/dashboard?merchant_id=1`
- `GET /api/v1/payouts/history?merchant_id=1&limit=20&offset=0`

## Tests

Run:

- `python backend/manage.py test payouts`

Included critical tests:
- idempotency replay does not duplicate payout
- concurrent overdraft attempts allow exactly one successful payout
- failed -> completed transition is rejected
- exhausted retries fail payout and refund held funds atomically

## Local Run (Docker Infra, Local App)

Start Postgres and Redis in Docker:

- `docker compose up -d postgres redis`

Then run the backend locally in a virtualenv:

- `.\.venv\Scripts\activate`
- `Remove-Item Env:USE_SQLITE -ErrorAction SilentlyContinue`
- `$env:POSTGRES_DB="playtopay"`
- `$env:POSTGRES_USER="postgres"`
- `$env:POSTGRES_PASSWORD="postgres"`
- `$env:POSTGRES_HOST="localhost"`
- `$env:POSTGRES_PORT="5432"`
- `$env:REDIS_URL="redis://127.0.0.1:6379/0"`
- `python backend/manage.py migrate`
- `python backend/manage.py seed_data`
- `python backend/manage.py runserver`

In another shell, start the worker with the same env vars:

- `.\.venv\Scripts\activate`
- `Remove-Item Env:USE_SQLITE -ErrorAction SilentlyContinue`
- `$env:POSTGRES_DB="playtopay"`
- `$env:POSTGRES_USER="postgres"`
- `$env:POSTGRES_PASSWORD="postgres"`
- `$env:POSTGRES_HOST="localhost"`
- `$env:POSTGRES_PORT="5432"`
- `$env:REDIS_URL="redis://127.0.0.1:6379/0"`
- `python backend/manage.py run_huey`

## Deployment Notes

- Backend can be deployed on Render/Railway/Fly with:
  - web command: `python manage.py migrate && python manage.py runserver 0.0.0.0:$PORT`
  - worker command: `python manage.py run_huey`
  - env vars: `POSTGRES_*`, `REDIS_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`
- Frontend can be deployed on Vercel/Netlify with `VITE_API_BASE_URL` pointing to backend URL.
