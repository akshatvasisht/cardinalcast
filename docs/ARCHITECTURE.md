# Architecture Documentation

This document details the architectural decisions, system components, and data flow for **CardinalCast**.

---

## Glossary

- **Wager:** A user bet on a weather outcome (e.g. temperature above a threshold); has status PENDING / WIN / LOSE.
- **WeatherSnapshot:** Stored observation (date, location, temperature, wind_speed) used for ingestion and wager resolution.
- **Credits:** In-app balance used to place wagers and receive payouts.

## System overview

CardinalCast is a Python backend (FastAPI) with a React frontend. The backend handles auth, wagers, weather ingestion, wager resolution, and daily reset; ML is used for odds. Models are versioned with Git LFS.

## Directory structure

```
/
├── backend/              # FastAPI app, SQLModel models, services
│   ├── main.py           # App entry, CORS, lifespan, routers
│   ├── models.py         # User, Wager, WeatherSnapshot, WeatherForecast, Odds
│   ├── database.py       # Session dependency
│   ├── auth.py           # JWT, get_current_user, password hashing
│   ├── ingestion_service.py  # Daily weather ingestion entry
│   ├── resolution.py     # resolve_wagers()
│   ├── reset_service.py  # Daily reset (no-op until daily claims added)
│   ├── scheduler.py      # APScheduler: ingestion, resolution, reset
│   ├── routers/         # auth_routes, wager_routes, odds_routes
│   └── odds_service/     # Odds/predictions (model_services, ingestion, daily tasks)
├── frontend/             # React (Vite) + TypeScript + shadcn/ui; dashboard, auth, wagers
├── ml_training/          # Training scripts for quantile regression models
├── alembic/              # DB migrations
├── data/                 # Historical weather data
├── docs/
└── ...
```

## Tech stack

| Category   | Technology   | Rationale                                      |
|-----------|---------------|------------------------------------------------|
| Backend   | Python (FastAPI) | API, auth, ML orchestration; replaces Spring Boot |
| Database  | PostgreSQL    | Replaces MySQL; relational consistency         |
| ORM       | SQLModel      | Pydantic + SQLAlchemy; single source for schema and API |
| Migrations| Alembic       | Versioned schema changes; DB_URL from env      |
| Data/ML   | Git LFS       | Model versioning for public cloning              |
| Frontend  | React (Vite) + TypeScript + shadcn | Interactive UI |

## Database schema and migrations

- **Schema** is defined in `backend/models.py`:
  - **users:** id, username, password_hash, credits_balance, created_at
  - **wagers:** id, user_id, amount, status (PENDING/WIN/LOSE), odds, created_at, resolved_at; forecast_date, target, bucket_low, bucket_high, base_payout_multiplier, jackpot_multiplier, winnings
  - **weather_snapshots:** id, date, location, temperature, wind_speed, precipitation, created_at
  - **weather_forecasts:** id, date, noaa_high_temp, noaa_avg_wind_speed, noaa_precip, created_at
  - **odds:** forecast_date, target, bucket_*, probability, base_payout_multiplier, jackpot_multiplier

- **Migrations** are managed by Alembic. `alembic/env.py` reads `DB_URL` from the environment and uses `SQLModel.metadata` from `backend.models`. Initial migration: `alembic/versions/001_initial_schema.py`. Run `alembic upgrade head` after PostgreSQL is installed and configured.

## Data Integrity & Settlement

### Preliminary Settlement Strategy
NOAA GHCNd data takes 45-60 days to be fully finalized/audited. To ensure a good user experience, we use an **Optimistic Settlement** strategy:
1. **Settlement**: Wagers are resolved using **Preliminary Data**, which is available via the NOAA CDO API within **1-3 days**.
2. **Self-Correction**: The ingestion pipeline (`ingestion_service.py`) runs daily with a lookback window (default 30 days). When NOAA updates preliminary records to finalized values, the database adapter (`db.py`) automatically **upserts** (overwrites) the local records.
3. **Consistency**: This ensures fast payouts while guaranteeing the database eventually matches the official climatological record. Note: We do *not* reverse payouts if data changes, as per standard sports betting "action goes as written" policy for finalized events, unless the error was egregious.

### Data Lifecycle Policy
To manage database bloat and ensure fast query execution over time, CardinalCast enforces a strict **1-year retention policy** for temporary operational data:
- A scheduled script (`backend/scripts/purge_data.py`) deletes records from `Wager`, `WeatherForecast`, `WeatherSnapshot`, and `Odds` tables that are older than 365 days.
- User accounts and historical aggregates remain unaffected to preserve account integrity.

## Data flow

1. **Input:** Weather API (ingestion), user actions (register, login, place wager).
2. **Processing:** Auth (JWT), wager validation and ML odds, resolution after weather actuals, daily reset (scheduler).
3. **Output:** Persisted in PostgreSQL; models versioned with Git LFS.

## Client–server (frontend)

The React app talks to the backend over REST. Auth: user logs in or registers, receives a JWT; the client stores it (e.g. localStorage) and sends `Authorization: Bearer <token>` on protected requests. Dashboard and wager flows use `GET /auth/me`, `GET /wagers`, `GET /odds`, and `POST /wagers` as documented in API.md.

## Scheduler (APScheduler)

Jobs run in-process with the FastAPI app (started in lifespan).

| Job        | Schedule (America/Chicago) | Action |
|------------|----------------------------|--------|
| Ingestion  | 6:00 daily                 | Fetch NOAA actuals and forecasts; store in weather_snapshots and weather_forecasts. |
| Resolution | 6:15 daily                 | Resolve pending wagers (WIN/LOSE), update credits. |
| Reset      | 0:00 daily                 | Daily reset (no-op until daily-claim state is added). |

Order: ingestion before resolution so new actuals are available; reset at midnight.

## Config and secrets

All secrets (DB URL, JWT secret, API keys) come from environment variables or a secure store. `.env.example` lists placeholders; `.env` is gitignored.

## Design constraints

- No Java in the product; backend is Python only.
- No production deployment scope in the current plan; localhost/portfolio focus.

### 4. Odds Calibration Strategy (Fact-Based)
To ensure the House Edge (target 5-7%) is mathematically sound and not arbitrary:
1.  **Uncertainty Source**: Use **RMSE** (Root Mean Squared Error) from the ML model's validation set, not historical standard deviation.
2.  **Probability Integration**: Calculate bucket probabilities by integrating the **Probability Density Function (PDF)** (Area Under Curve) rather than fixed sigma ranges.
3.  **Safety Floor**: Minimum payout multiplier set to `1.01x` (industry standard -10000) to allow "sure thing" bets without giving away free value.

### 5. Deployment
- **Frontend**: Vercel (CI/CD from GitHub).

## Security Audit (Feb 2026)
- **Backend**: `bandit` scan passed with **0 issues** (clean).
- **Frontend**: `npm audit` flagged 2 moderate issues in `esbuild` (Vite dev dependency). Low risk for production build artifacts; scheduled for update with Vite 6.
