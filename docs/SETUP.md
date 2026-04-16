# Environment Setup Instructions

## Prerequisites

- Python 3.10+
- PostgreSQL
- Node.js 18+

## Installation

### 1. Clone & install

```bash
git clone https://github.com/username/cardinalcast.git
cd cardinalcast
```

Backend:

```bash
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the repo root (use [.env.example](../.env.example) as a template). Do not commit `.env`.

| Variable     | Required | Description                    |
|-------------|----------|--------------------------------|
| `DB_URL`    | Yes      | PostgreSQL URL (e.g. `postgresql://user:pass@localhost:5432/cardinalcast`) |
| `JWT_SECRET`   | Yes  | Secret for JWT signing (min 32 chars recommended) |
| `NOAA_CDO_TOKEN` | No* | NOAA CDO API token for ingestion |
| `ML_MODEL_DIR` | No  | Path to ML model `.pkl` files (default: `backend/odds_service/models`) |

\* Required for weather ingestion (actuals from NOAA CDO). Not needed for local demo — DB can be seeded manually.

Example:

```bash
# Required
DB_URL=postgresql://user:password@localhost:5432/cardinalcast
JWT_SECRET=your_jwt_secret_here
```

### 3. Database migrations (Alembic)

Migrations are in `alembic/versions/`. **Do not run migrations until PostgreSQL is installed and `DB_URL` is set.**

When the DB is ready:

```bash
# Create/update tables
alembic upgrade head
```

To generate a new migration after changing `backend/models.py`:

```bash
alembic revision --autogenerate -m "description"
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for schema and migration strategy.

### 4. Frontend

Node.js 18+ required. From the repo root:

```bash
cd frontend
npm install
```

Create `frontend/.env` (or set in the shell) with:

| Variable        | Required | Description                          |
|----------------|----------|--------------------------------------|
| `VITE_API_URL` | No       | Backend base URL (default: `http://localhost:8000`) |
| `VITE_DEV_BYPASS_AUTH` | No  | Set to `true` (dev only) to open the app without logging in and test the gambling UI (dashboard, place wager, history). |

Then run the dev server:

```bash
npm run dev
```

The app is served at http://localhost:5173. **The backend must be running** (see below) for auth, wagers, and odds to work.

## Running the application

- **Backend (development):** From the repo root with `DB_URL` and `JWT_SECRET` set in `.env`:
  ```bash
  uvicorn backend.main:app --reload
  ```
  OpenAPI docs: http://127.0.0.1:8000/docs
- **Frontend (development):** From `frontend/` run `npm run dev`; open http://localhost:5173.

## Running Tests

Please refer to [TESTING.md](TESTING.md) for detailed test coverage and instructions on running the backend and E2E test suites.

## Troubleshooting

- **Alembic "Can't locate revision":** Ensure you run `alembic upgrade head` from the repo root with `DB_URL` set.
- **ImportError for backend:** Run Alembic from the repo root so `backend` is on `PYTHONPATH` (or use `prepend_sys_path = .` in alembic.ini, which is already set).
- **Tests fail with "connection refused":** PostgreSQL must be running. Check with `pg_isready`.
- **Tests fail with "password authentication failed":** Ensure `DB_URL` env var is set correctly — without it, the app falls back to a default that won't match your local DB credentials.
