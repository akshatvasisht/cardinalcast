# Testing Guidelines

12 backend tests (pytest) and 6 E2E tests (Playwright) cover critical paths: auth, wager validation, odds API, user journeys, navigation, and accessibility basics.


## Backend Tests (pytest)

### Running Tests

```bash
# From backend directory
cd backend
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=backend --cov-report=term-missing
```

### Test Coverage

The test suite includes unit tests for the backend (Health, Auth, Wager Validation, Odds API, and User Profiles) using an actual PostgreSQL instance.

### Mocking Strategy

- **Database**: Tests use a real PostgreSQL instance (local; configure via `DB_URL` in `.env`) — a dedicated test database would be used in production
- **ML Models**: Mock `backend.odds_service.load_models` where needed
- **External APIs**: Mock NOAA API calls for ingestion tests


## Frontend Tests (Playwright)

### Running Tests

```bash
# From frontend directory
cd frontend

# Run tests headless
npm run test:e2e

# Run tests with UI (interactive mode)
npm run test:e2e:ui

# Run tests with browser visible
npm run test:e2e:headed
```

### Test Coverage

E2E tests verify user journeys, accessibility, and component visibility across dashboard and application states.

## Profitability backtest

The script `ml_training/backtest_profitability.py` validates that the house stays profitable with the current odds pricing (simulates betting on the "Favorite" bucket over historical data). Run from the repo root after generating cleaned weather data:

```bash
# From repo root (ensure data/cleaned_weather_data.csv exists; run data_cleaning.py first if needed)
python ml_training/backtest_profitability.py
```

Exit code 0 means the house is profitable; exit code 1 means the backtest failed or the house would lose money with current settings.
