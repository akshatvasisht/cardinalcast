# Coding Standards & Style Guide

This document defines the coding standards, conventions, and best practices for the CardinalCast weather wagering platform. All code must follow these guidelines to ensure quality, maintainability, and consistency.

---

## Table of Contents

1. [General Principles](#general-principles)
2. [Python Guidelines](#python-guidelines)
3. [TypeScript/React Guidelines](#typescriptreact-guidelines)
4. [SQL & Database](#sql--database)
5. [Testing Standards](#testing-standards)
6. [Security & Error Handling](#security--error-handling)
7. [Performance Guidelines](#performance-guidelines)
8. [Documentation Standards](#documentation-standards)
9. [Git Workflow](#git-workflow)
10. [Code Review Checklist](#code-review-checklist)

---

## General Principles

- **Clarity over cleverness**: Code should be self-explanatory
- **Explicit is better than implicit**: Type annotations, error messages, and intent should be clear
- **Fail fast**: Validate inputs early and raise meaningful errors
- **Production mindset**: Even demo code should follow production patterns

---

## Python Guidelines

### Version & Environment

- **Python 3.10+** required
- Use virtual environments (`.venv`) - never install globally
- Pin dependencies in `requirements.txt` with exact versions

### Naming Conventions

| Element          | Convention           | Example                              |
| ---------------- | -------------------- | ------------------------------------ |
| Variables        | snake_case           | `user_balance`, `is_processing`      |
| Functions        | snake_case           | `place_wager()`, `resolve_wagers()`  |
| Constants        | SCREAMING_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT`     |
| Classes          | PascalCase           | `User`, `WagerService`, `OddsEngine` |
| Private vars     | `_underscore`        | `_session`, `_cached_model`          |
| Modules          | snake_case           | `model_services.py`, `auth.py`       |
| Test files       | `test_*.py`          | `test_demo.py`, `test_wagers.py`     |

### Type Annotations

All public functions must have type annotations:

```python
# Good: Explicit types
def calculate_odds(
    p10: float,
    p50: float,
    p90: float,
    house_edge: float = 0.10
) -> dict[str, float]:
    """Calculate bucket odds from quantile predictions."""
    spread = p90 - p10
    return {"spread": spread, "risk_score": spread / p50}

# Bad: No types
def calculate_odds(p10, p50, p90, house_edge=0.10):
    spread = p90 - p10
    return {"spread": spread, "risk_score": spread / p50}
```

### FastAPI Patterns

#### Endpoint Structure

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from backend.database import get_session
from backend.auth import get_current_user
from backend.models import User, Wager

router = APIRouter(prefix="/wagers", tags=["wagers"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def place_wager(
    wager_request: WagerRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> WagerResponse:
    """Place a wager on a weather outcome."""
    # Validate balance
    if current_user.credits_balance < wager_request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits"
        )

    # Create wager
    wager = Wager(**wager_request.model_dump(), user_id=current_user.id)
    session.add(wager)
    session.commit()
    session.refresh(wager)

    return WagerResponse.model_validate(wager)
```

#### Pydantic/SQLModel Models

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    """User model for authentication and credits."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    credits_balance: int = Field(default=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# API schemas (no table=True)
class WagerRequest(SQLModel):
    forecast_date: str
    target: str
    bucket_value: float
    amount: int
```

### ML Code Patterns

#### Model Training

```python
import xgboost as xgb
import optuna
import joblib
from pathlib import Path
from sklearn.metrics import mean_absolute_error

def train_quantile_model(
    X: pd.DataFrame,
    y: pd.Series,
    quantile: float,
    n_trials: int = 10
) -> xgb.XGBRegressor:
    """
    Train XGBoost quantile regression model with Optuna tuning.

    Args:
        X: Feature matrix
        y: Target vector
        quantile: Target quantile (0.1, 0.5, or 0.9)
        n_trials: Number of Optuna trials

    Returns:
        Trained XGBoost model
    """
    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective": "reg:quantileerror",
            "quantile_alpha": quantile,
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
        }

        model = xgb.XGBRegressor(**params, random_state=67)
        model.fit(X, y)
        preds = model.predict(X)
        return mean_absolute_error(y, preds)

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    best_model = xgb.XGBRegressor(
        **study.best_params,
        objective="reg:quantileerror",
        quantile_alpha=quantile,
        random_state=67
    )
    best_model.fit(X, y)

    return best_model
```

#### Feature Engineering

```python
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate time series features for weather prediction.

    Creates:
    - Cyclical temporal encodings (sin/cos)
    - Rolling window statistics (3/7/14/30 days)
    - Lag features (1/2/3 days)
    - Meteorological interactions
    """
    df = df.copy()

    # Cyclical temporal features
    df["day_of_year_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["day_of_year_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

    # Rolling windows
    for window in [3, 7, 14, 30]:
        df[f"high_temp_last_{window}d_avg"] = (
            df["high_temp"].rolling(window).mean()
        )

    # Lag features
    for lag in [1, 2, 3]:
        df[f"high_temp_lag_{lag}"] = df["high_temp"].shift(lag)

    # Interaction features
    df["temp_range_x_precip"] = (
        (df["high_temp"] - df["low_temp"]) * df["precip"]
    )

    return df.dropna()  # Remove rows with NaN from rolling/lag
```

### Error Handling

```python
from fastapi import HTTPException, status

# Good: Specific error with detail
if not odds_row:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No odds found for target={target} on date={forecast_date}"
    )

# Good: Wrap external errors
try:
    model = joblib.load(model_path)
except FileNotFoundError as e:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Model file not found: {model_path}"
    ) from e

# Bad: Generic error
raise Exception("Something went wrong")
```

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Feature engineering started")  # Development detail
logger.info("Loaded 8472 samples for training")  # Important events
logger.warning("NOAA API rate limit approaching")  # Potential issues
logger.error("Failed to load model file", exc_info=True)  # Errors with traceback
```

---

## TypeScript/React Guidelines

### Version & Environment

- **TypeScript 5.6+** with strict mode
- **React 18+** with hooks
- **Vite** for build tooling

### Naming Conventions

| Element            | Convention     | Example                              |
| ------------------ | -------------- | ------------------------------------ |
| Variables          | camelCase      | `userBalance`, `isLoading`           |
| Functions          | camelCase      | `placeWager()`, `handleClick()`      |
| Constants          | SCREAMING_CASE | `MAX_WAGER_AMOUNT`, `API_BASE_URL`   |
| Types/Interfaces   | PascalCase     | `WagerRequest`, `User`               |
| Components         | PascalCase     | `PlaceWagerDialog`, `DayDetailPanel` |
| Files (components) | PascalCase     | `PlaceWagerDialog.tsx`, `Layout.tsx` |
| Files (utils)      | camelCase      | `api.ts`, `utils.ts`                 |

### TypeScript Strict Mode

All TypeScript must compile with strict mode:

```typescript
// tsconfig.json (required)
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true
  }
}

// Good: Explicit types
interface WagerRequest {
  forecast_date: string;
  target: "high_temp" | "avg_wind_speed" | "precipitation";
  bucket_value: number;
  amount: number;
}

async function placeWager(request: WagerRequest): Promise<WagerResponse> {
  const response = await fetch(`${API_BASE_URL}/wagers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to place wager: ${response.statusText}`);
  }

  return response.json() as Promise<WagerResponse>;
}

// Bad: Implicit any
async function placeWager(request) {
  const response = await fetch(`/wagers`, {
    method: "POST",
    body: JSON.stringify(request),
  });
  return response.json();
}
```

### React Component Structure

```typescript
import { useState, useEffect } from "react";
import { WagerService } from "../services/wagerService";
import { Button } from "./ui/button";

// =============================================================================
// Types
// =============================================================================

interface PlaceWagerDialogProps {
  forecastDate: string;
  onSuccess: (wagerId: number) => void;
  onCancel: () => void;
}

type WagerTarget = "high_temp" | "avg_wind_speed" | "precipitation";

// =============================================================================
// Component
// =============================================================================

export function PlaceWagerDialog({
  forecastDate,
  onSuccess,
  onCancel,
}: PlaceWagerDialogProps) {
  // State
  const [target, setTarget] = useState<WagerTarget>("high_temp");
  const [amount, setAmount] = useState<number>(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Effects
  useEffect(() => {
    // Load odds for selected target
    loadOdds(forecastDate, target);
  }, [forecastDate, target]);

  // Handlers
  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await WagerService.place({
        forecast_date: forecastDate,
        target,
        bucket_value: 77.5,
        amount,
      });

      onSuccess(response.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render
  return (
    <div className="dialog">
      <h2>Place Wager</h2>
      {error && <div className="error" role="alert">{error}</div>}

      <select value={target} onChange={(e) => setTarget(e.target.value as WagerTarget)}>
        <option value="high_temp">High Temperature</option>
        <option value="avg_wind_speed">Avg Wind Speed</option>
        <option value="precipitation">Precipitation</option>
      </select>

      <input
        type="number"
        value={amount}
        onChange={(e) => setAmount(Number(e.target.value))}
        min={1}
        aria-label="Wager amount"
      />

      <div className="actions">
        <Button onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? "Placing..." : "Place Wager"}
        </Button>
        <Button onClick={onCancel} variant="outline">
          Cancel
        </Button>
      </div>
    </div>
  );
}
```

### Accessibility

All components must be accessible:

1. **Semantic HTML** — Use `<button>`, `<nav>`, `<main>`, `<article>`
2. **ARIA labels** — Provide `aria-label` for non-text elements
3. **ARIA states** — Use `aria-busy`, `aria-disabled`, `aria-pressed`
4. **Keyboard support** — All interactive elements must be keyboard accessible
5. **Focus management** — Visible focus indicators, logical tab order

```tsx
<button
  onClick={handleWager}
  disabled={isProcessing}
  aria-label={isProcessing ? "Processing wager..." : "Place wager"}
  aria-busy={isProcessing}
  type="button"
>
  Place Wager
</button>
```

### CSS (Tailwind + CSS Variables)

Use semantic CSS variables defined in `globals.css`:

```css
/* globals.css */
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --success: 142.1 76.2% 36.3%;
    --destructive: 0 84.2% 60.2%;
    --warning: 38 92% 50%;
  }
}

/* Use in components */
.wager-status {
  color: hsl(var(--success)); /* Win */
  color: hsl(var(--destructive)); /* Lose */
  color: hsl(var(--warning)); /* Pending */
}
```

In React components:

```tsx
// Good: Semantic class names
<span className="text-success">Won</span>
<span className="text-destructive">Lost</span>
<span className="text-warning">Pending</span>

// Bad: Hardcoded colors
<span className="text-green-600">Won</span>
<span className="text-red-600">Lost</span>
```

---

## SQL & Database

### Alembic Migrations

All schema changes must go through Alembic:

```bash
# Create migration after modifying backend/models.py
alembic revision --autogenerate -m "add wager_type column"

# Review generated migration before running
# Edit alembic/versions/XXX_add_wager_type_column.py if needed

# Apply migration
alembic upgrade head
```

Migration naming:
- `001_initial_schema.py`
- `002_add_odds_table.py`
- `003_add_wager_type.py`

### SQL Patterns

Use SQLModel query syntax (not raw SQL):

```python
from sqlmodel import select, Session

# Good: Type-safe queries
def get_user_wagers(user_id: int, session: Session) -> list[Wager]:
    statement = (
        select(Wager)
        .where(Wager.user_id == user_id)
        .order_by(Wager.created_at.desc())
    )
    return session.exec(statement).all()

# Bad: Raw SQL strings
def get_user_wagers(user_id: int, session: Session):
    result = session.execute(
        f"SELECT * FROM wagers WHERE user_id = {user_id}"
    )
    return result.fetchall()
```

---

## Testing Standards

### Backend Tests (pytest)

Test file structure:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestAuthentication:
    def test_register_new_user(self):
        """Should create user and return JWT token"""
        response = client.post("/auth/register", json={
            "username": "testuser123",
            "password": "securepass"
        })

        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    def test_register_duplicate_username(self):
        """Should reject duplicate username with 400"""
        # Arrange: Create user
        client.post("/auth/register", json={
            "username": "duplicate",
            "password": "pass123"
        })

        # Act: Try to create again
        response = client.post("/auth/register", json={
            "username": "duplicate",
            "password": "pass456"
        })

        # Assert
        assert response.status_code == 400
```

### Frontend Tests (Playwright)

```typescript
import { test, expect } from "@playwright/test";

test.describe("Wager Placement", () => {
  test("should place bucket wager successfully", async ({ page }) => {
    // Arrange: Login
    await page.goto("/login");
    await page.fill('input[name="username"]', "testuser");
    await page.fill('input[name="password"]', "testpass");
    await page.click('button[type="submit"]');

    // Act: Place wager
    await page.goto("/dashboard");
    await page.click("text=Place Wager");
    await page.selectOption('select[name="target"]', "high_temp");
    await page.fill('input[name="amount"]', "10");
    await page.click('button:has-text("Confirm")');

    // Assert
    await expect(page.locator("text=Wager placed successfully")).toBeVisible();
  });
});
```

### Test Coverage Philosophy

**Current**: Demo-level tests (11 backend, 4 E2E) to showcase capability

**Production**: Would include:
- Unit tests: 80%+ coverage
- Integration tests: Critical flows
- Load tests: Performance validation
- Security tests: Penetration testing

---

## Security & Error Handling

### JWT Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
```

### Input Validation

Always validate external input:

```python
from pydantic import validator, Field

class WagerRequest(SQLModel):
    forecast_date: str = Field(regex=r"^\d{4}-\d{2}-\d{2}$")
    target: Literal["high_temp", "avg_wind_speed", "precipitation"]
    bucket_value: float = Field(gt=0, lt=200)
    amount: int = Field(ge=1, le=1000)

    @validator("forecast_date")
    def validate_future_date(cls, v):
        date_obj = datetime.strptime(v, "%Y-%m-%d")
        if date_obj < datetime.now():
            raise ValueError("Cannot wager on past dates")
        return v
```

---

## Performance Guidelines

### Database Query Optimization

```python
# Good: Single query with join
statement = (
    select(Wager, User)
    .join(User)
    .where(Wager.status == "PENDING")
)
results = session.exec(statement).all()

# Bad: N+1 query problem
wagers = session.exec(select(Wager)).all()
for wager in wagers:
    user = session.get(User, wager.user_id)  # N queries!
```

### Model Loading

Cache loaded ML models to avoid repeated disk I/O:

```python
# Global cache
_model_cache: dict[str, xgb.XGBRegressor] = {}

def load_model(model_path: Path) -> xgb.XGBRegressor:
    """Load model with caching."""
    cache_key = str(model_path)

    if cache_key not in _model_cache:
        _model_cache[cache_key] = joblib.load(model_path)

    return _model_cache[cache_key]
```

---

## Documentation Standards

### Docstrings (Python)

Use Google style docstrings:

```python
def train_quantile_model(
    X: pd.DataFrame,
    y: pd.Series,
    quantile: float,
    n_trials: int = 10
) -> xgb.XGBRegressor:
    """
    Train XGBoost quantile regression model with Optuna tuning.

    Uses Bayesian optimization to find optimal hyperparameters for
    predicting the specified quantile of the target distribution.

    Args:
        X: Feature matrix with shape (n_samples, n_features)
        y: Target vector with shape (n_samples,)
        quantile: Target quantile (0.1 for P10, 0.5 for P50, 0.9 for P90)
        n_trials: Number of Optuna optimization trials (default: 10)

    Returns:
        Trained XGBoost model fitted on (X, y)

    Raises:
        ValueError: If quantile not in range [0, 1]

    Example:
        >>> X_train, y_train = prepare_data(df, "high_temp")
        >>> model_p50 = train_quantile_model(X_train, y_train, quantile=0.5)
        >>> predictions = model_p50.predict(X_test)
    """
    if not 0 <= quantile <= 1:
        raise ValueError(f"Quantile must be in [0, 1], got {quantile}")

    # ... implementation
```

### Comments

```python
# Good: Explains WHY
# Use optimistic settlement: resolve with preliminary NOAA data (1-3 day lag)
# instead of waiting 45-60 days for finalized records. Ensures fast payouts.
wager.status = resolve_with_preliminary_data(weather_snapshot)

# Bad: Explains WHAT (already obvious from code)
# Set wager status to WIN
wager.status = "WIN"
```

---

## Git Workflow

### Branch Naming

| Type     | Pattern        | Example                      |
| -------- | -------------- | ---------------------------- |
| Feature  | `feature/desc` | `feature/quantile-models`    |
| Bug fix  | `fix/desc`     | `fix/wager-validation`       |
| Refactor | `refactor/desc`| `refactor/odds-calculation`  |
| Docs     | `docs/desc`    | `docs/api-documentation`     |

### Commit Messages

Use imperative mood:

```
# Good
Add quantile regression models for uncertainty modeling
Fix wager placement validation
Update API documentation

# Bad
Added quantile regression models
Fixed bug
Documentation update
```

### Commit Scope

One logical change per commit:

```bash
# Good
git commit -m "Add P10/P50/P90 quantile models"
git commit -m "Add Optuna hyperparameter tuning"
git commit -m "Add metrics logging to training pipeline"

# Bad
git commit -m "Add models, tuning, metrics, and fix tests"
```

---

## Code Review Checklist

### Before Requesting Review

- [ ] Code passes type checking (`mypy` for Python, `tsc` for TypeScript)
- [ ] All tests pass (`pytest -v`, `npm run test:e2e`)
- [ ] No linter warnings (`ruff` for Python, `eslint` for TypeScript)
- [ ] Added tests for new functionality
- [ ] Updated relevant documentation
- [ ] Removed debugging code and print statements

### Reviewer Checklist

- [ ] Code follows style guide
- [ ] Logic is correct and handles edge cases
- [ ] Error messages are actionable
- [ ] No security vulnerabilities (SQL injection, XSS, etc.)
- [ ] Performance implications considered
- [ ] Accessibility requirements met (frontend)
- [ ] Tests are meaningful
- [ ] Documentation is accurate

---

## Tool Configuration

### Python (pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["backend/tests"]
python_files = "test_*.py"
```

### TypeScript (tsconfig.json)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

---

## Architecture Patterns Summary

### Backend Patterns

1. **FastAPI + SQLModel** — Single schema definition for DB and API
2. **Alembic Migrations** — Versioned schema changes
3. **JWT Authentication** — Stateless auth with Bearer tokens
4. **Dependency Injection** — Use FastAPI `Depends()` for session, auth

### ML Patterns

1. **Quantile Regression** — Model uncertainty with P10/P50/P90
2. **RFECV** — Automatic feature selection
3. **Optuna** — Bayesian hyperparameter optimization
4. **Time Series CV** — Prevent data leakage with `TimeSeriesSplit`

### Frontend Patterns

1. **React Hooks** — Functional components with `useState`, `useEffect`
2. **TypeScript Strict** — Full type safety across components
3. **Semantic CSS** — Use CSS variables (`--success`, `--destructive`)
4. **Accessibility** — ARIA labels, keyboard navigation, focus management

---

**Last Updated**: 2026-03-11
