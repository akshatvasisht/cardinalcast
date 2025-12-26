# Testing Guidelines

## Overview

CardinalCast includes **demonstration-quality tests** to showcase testing capability for a portfolio project. For production deployment, comprehensive test coverage (80%+) would be implemented.

## Testing Philosophy

**Current Approach**: Demo tests covering critical paths to demonstrate:
- Understanding of testing frameworks (pytest, Playwright)
- API testing patterns (authentication, validation)
- E2E user journey testing
- Accessibility testing basics

**Production Approach**: Would include:
- Comprehensive unit tests (80%+ coverage)
- Integration tests (full user flows)
- Load tests (performance validation)
- Security tests (penetration testing)
- Visual regression tests
- Cross-browser testing

---

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

Current demo tests cover:

#### **Authentication** (`test_demo.py::TestAuthentication`)
- ✅ User registration with valid credentials
- ✅ Duplicate username rejection
- ✅ Login with valid credentials
- ✅ Login with invalid password
- ✅ Login with nonexistent user

#### **Wager Validation** (`test_demo.py::TestWagerValidation`)
- ✅ Authentication requirement enforcement
- ✅ Insufficient balance rejection
- ✅ Minimum wager amount validation

#### **Odds API** (`test_demo.py::TestOddsAPI`)
- ✅ Odds list retrieval
- ✅ Response schema validation

#### **User Profile** (`test_demo.py::TestUserProfile`)
- ✅ Current user profile retrieval
- ✅ Initial balance verification

### Mocking Strategy

- **Database**: Tests use real PostgreSQL (via Docker) - would use test database in production
- **ML Models**: Mock `backend.odds_service.load_models` where needed
- **External APIs**: Mock NOAA API calls for ingestion tests

---

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

Current E2E tests cover:

#### **User Journeys** (`smoke.spec.ts`)
- ✅ Registration → Login → Daily claim flow
- ✅ Place bucket wager
- ✅ Place over/under wager
- ✅ Wager history verification
- ✅ Leaderboard visibility

#### **Accessibility** (`smoke.spec.ts`)
- ✅ Homepage branding and navigation
- ✅ Keyboard navigation through forms
- ✅ Screen reader landmarks (implicit)

#### **Component Visibility** (`smoke.spec.ts`)
- ✅ Dashboard components (calendar, map, wager widget)
- ✅ Navigation between all pages
- ✅ Logo and branding elements

### Production E2E Tests Would Include

- Cross-browser testing (Chrome, Firefox, Safari)
- Mobile viewport testing (320px to 1920px)
- Accessibility audits (axe-core integration)
- Visual regression tests (Percy, Chromatic)
- Performance testing (Lighthouse CI)

## Profitability backtest

The script `ml_training/backtest_profitability.py` validates that the house stays profitable with the current odds pricing (simulates betting on the "Favorite" bucket over historical data). Run from the repo root after generating cleaned weather data:

```bash
# From repo root (ensure data/cleaned_weather_data.csv exists; run data_cleaning.py first if needed)
python ml_training/backtest_profitability.py
```

Exit code 0 means the house is profitable; exit code 1 means the backtest failed or the house would lose money with current settings.
