# Architecture Documentation

## Glossary

- **Wager:** A user bet on a weather outcome (e.g. temperature above a threshold); has status PENDING / PENDING_DATA / WIN / LOSE.
- **WeatherSnapshot:** Stored observation (date, location, temperature, wind_speed) used for ingestion and wager resolution.
- **Credits:** In-app balance used to place wagers and receive payouts.

## System overview

CardinalCast is a Python backend (FastAPI) with a React frontend. The backend handles auth, wagers, weather ingestion, wager resolution, and daily reset; ML is used for odds. Models are versioned with Git LFS.

## Directory structure

```
/
├── backend/              # FastAPI app, SQLModel models, services
│   ├── main.py           # App entry, CORS, GZip middleware, lifespan, routers
│   ├── models.py         # User, Wager, WeatherSnapshot, WeatherForecast, Odds
│   ├── database.py       # Session dependency
│   ├── auth.py           # JWT, get_current_user, get_current_user_optional, password hashing
│   ├── config.py         # Business logic constants (max wager, house edge, etc.)
│   ├── resolution.py     # resolve_wagers()
│   ├── reset_service.py  # Daily reset logic (called by scheduler)
│   ├── lifecycle_service.py  # Data retention purge (called by scheduler)
│   ├── scheduler.py      # APScheduler: purge, ingestion, resolution, reset
│   ├── Dockerfile        # Container image for the backend
│   ├── routers/          # auth_routes, wager_routes, odds_routes, daily_routes, leaderboard_routes
│   └── odds_service/     # Odds/predictions facade
│       ├── model_services.py
│       ├── feature_engineering.py
│       ├── ingestion_service.py
│       ├── payout_logic.py
│       ├── daily_tasks.py
│       ├── db.py         # DB helpers for scheduler jobs
│       ├── config.py
│       └── models/       # Trained .pkl model files (Git LFS)
├── frontend/             # React (Vite) + TypeScript + shadcn/ui; dashboard, auth, wagers
│   └── tests/e2e/        # Playwright smoke tests
├── ml_training/          # Training scripts for quantile regression models
├── alembic/              # DB migrations
├── data/                 # Historical weather data
├── docs/
└── ...
```

## Tech stack

| Category   | Technology   | Rationale                                      |
|-----------|---------------|------------------------------------------------|
| Backend   | Python (FastAPI) | API, auth, ML orchestration                       |
| Database  | PostgreSQL    | Relational consistency; production-grade       |
| ORM       | SQLModel      | Pydantic + SQLAlchemy; single source for schema and API |
| Migrations| Alembic       | Versioned schema changes; DB_URL from env      |
| Data/ML   | Git LFS       | Model versioning for public cloning              |
| Frontend  | React (Vite) + TypeScript + shadcn | Interactive UI |

## Database schema and migrations

- **Schema** is defined in `backend/models.py`:
  - **users:** id, username, password_hash, credits_balance, created_at, last_daily_claim_date
  - **wagers:** id, user_id, amount, status (PENDING/PENDING_DATA/WIN/LOSE), odds, created_at, resolved_at; forecast_date, target, wager_kind (BUCKET/OVER_UNDER), bucket_low, bucket_high, direction (OVER/UNDER, nullable), predicted_value (float, nullable), target_value (float), base_payout_multiplier, jackpot_multiplier, winnings
  - **weather_snapshots:** id, date, location, temperature, wind_speed, precipitation, created_at
  - **weather_forecasts:** id, date, noaa_high_temp, noaa_avg_wind_speed, noaa_precip, created_at
  - **odds:** forecast_date, target, bucket_*, probability, base_payout_multiplier, jackpot_multiplier

- **Migrations** are managed by Alembic. `alembic/env.py` reads `DB_URL` from the environment and uses `SQLModel.metadata` from `backend.models`. Initial migration: `alembic/versions/001_initial_schema.py`.
## Data Integrity & Settlement

### Preliminary Settlement Strategy
NOAA GHCNd data takes 45-60 days to be fully finalized/audited. Wagers are resolved against **preliminary data**, which NOAA makes available within 1-3 days, allowing fast payouts without waiting for the finalized record.

The ingestion pipeline (`ingestion_service.py`) runs daily with a 30-day lookback window. When NOAA updates preliminary records with finalized values, `db.py` upserts them automatically — the local database converges to the official climatological record over time. Payouts are not reversed after settlement, consistent with the standard sports betting "action goes as written" policy.

### Data Retention Policy
To prevent unbounded table growth, CardinalCast enforces a **1-year retention policy** for temporary operational data:
- A scheduled job (`backend/lifecycle_service.py`) deletes records from `WeatherForecast` and `WeatherSnapshot` tables that are older than 365 days.
- User accounts and historical aggregates remain unaffected to preserve account integrity.

## Scheduler (APScheduler)

Jobs run in-process with the FastAPI app (started in lifespan).

| Job        | Schedule (America/Chicago) | Action |
|------------|----------------------------|--------|
| Purge      | 4:00 daily                 | Delete `WeatherForecast` and `WeatherSnapshot` records older than 365 days. Wagers and odds are retained. |
| Ingestion  | 6:00 daily                 | Fetch NOAA actuals and forecasts; store in weather_snapshots and weather_forecasts; generate odds. |
| Resolution | 6:15 daily                 | Resolve pending wagers (WIN/LOSE), update credits. |
Order: purge at 4 AM to clear stale data; ingestion before resolution so new actuals are available. Daily credit claims are user-triggered (idempotent per calendar day) -- no scheduled job required.

## Config and secrets

All secrets (DB URL, JWT secret, API keys) come from environment variables or a secure store. `.env.example` lists placeholders; `.env` is gitignored.

## Design constraints

- Localhost/portfolio scope — no production deployment pipeline.

## Odds Calibration

House edge target: 5–10%. Approach:
- Use RMSE from model validation set as the uncertainty source (not historical standard deviation).
- Calculate bucket probabilities by integrating the quantile PDF (area under curve), not fixed sigma ranges.
- Safety floor: minimum payout multiplier `1.01x`; ceiling `50x`. Configured in `backend/config.py`.
- Uncertainty scaling factor (1.5–2.0×) applied to model spread for forecasts >3 days out.

