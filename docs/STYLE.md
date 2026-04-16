# Coding Standards & Style Guide

## General Principles

- **Clarity over cleverness**: Code should be self-explanatory
- **Explicit is better than implicit**: Type annotations, error messages, and intent should be clear
- **Fail fast**: Validate inputs early and raise meaningful errors
- **Production mindset**: Even demo code should follow production patterns


## Python Guidelines

### Version & Environment

- **Python 3.10+** required
- Use virtual environments (`venv/`) - never install globally
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

All public functions must have type annotations. Use built-in generics (`dict[str, float]`, `list[int]`) rather than `typing.Dict`/`typing.List`.

### FastAPI Patterns

#### Endpoint Structure

```python
# Provide dependency injection for auth and db session in router endpoints.
@router.post("/", status_code=status.HTTP_201_CREATED)
async def place_wager(
    wager_request: WagerRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    pass
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
    credits_balance: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# API schemas (no table=True)
class WagerRequest(SQLModel):
    forecast_date: str
    target: str
    bucket_value: float
    amount: int
```

### ML Code Patterns

Training and feature engineering patterns are implemented in `ml_training/train_models.py` and `ml_training/feature_engineering.py`. Key conventions:
- XGBoost quantile regression via `objective='reg:quantileerror'`, one model per quantile (P10/P50/P90)
- Bayesian hyperparameter search with Optuna (`TimeSeriesSplit` to prevent data leakage)
- Feature selection via `RFECV`; serialize selector + models with `joblib`
- Cyclical temporal encodings (sin/cos), rolling windows (3/7/14/30d), lag features, meteorological interactions

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

All TypeScript must compile with `strict: true` (`noImplicitAny`, `strictNullChecks`, `noUnusedLocals`). See `frontend/tsconfig.json`.

### React Component Structure

Functional components only. Structure files as: types → component → handlers → render. Group related state; keep effects scoped to a single concern.

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

CSS variables are defined in `src/index.css` using **oklch** color space (not HSL):

```css
/* src/index.css */
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --primary: oklch(0.41 0.22 25);       /* UW Madison Cardinal Red */
  --success: oklch(0.623 0.169 149.185);
  --destructive: oklch(0.577 0.245 27.325);
  --warning: oklch(0.769 0.188 70.08);
  /* Medal tokens for leaderboard */
  --medal-gold: oklch(0.78 0.17 85);
  --medal-silver: oklch(0.72 0 0);
  --medal-bronze: oklch(0.62 0.10 55);
}

/* Dark mode — all tokens override under .dark class */
.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --primary: oklch(0.55 0.22 25);
  /* ... */
}
```

Tokens are full `oklch(...)` values — use them directly, not via `hsl(var(...))`:

```tsx
// Good: semantic Tailwind token classes
<span className="text-success">Won</span>
<span className="text-destructive">Lost</span>
<span className="text-warning">Pending</span>

// Bad: hardcoded palette classes
<span className="text-green-600">Won</span>
<span className="text-red-600">Lost</span>
```

### Visual Identity

**BalatroBackground** — WebGL shader component (`src/components/BalatroBackground.tsx`) used as a full-bleed background on the app layout and auth pages. Pauses the animation loop when the browser tab is hidden to avoid background CPU burn. Colors are centralized in `src/lib/constants.ts`:

```ts
export const BALATRO_COLORS = {
  color1: '#C5050C',  // Cardinal Red
  color2: '#FFFFFF',
  color3: '#1a1a1a',
} as const
```

**Glassmorphism** — Cards use `bg-card/90 backdrop-blur-sm` for a frosted glass effect against the Balatro background. Applied in `src/components/ui/Card.tsx`.

**Font** — `Outfit` (Google Fonts), loaded with weights 400/500/600/700. Defined in `src/index.css` via `@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap')`.


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


## Testing Standards

See [TESTING.md](TESTING.md) for test structure, coverage details, and run commands.


## Security & Error Handling

### JWT Authentication

```python
# Implement JWT authentication by securely verifying signatures and parsing the payload.
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    # Use PyJWT or python-jose to decode credentials.
    raise NotImplementedError
```

### Input Validation

Always validate external input:

```python
from pydantic import field_validator, Field

class WagerRequest(SQLModel):
    forecast_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    target: Literal["high_temp", "avg_wind_speed", "precipitation"]
    bucket_value: float = Field(gt=0, lt=200)
    amount: int = Field(ge=1, le=1000)

    @field_validator("forecast_date")
    @classmethod
    def validate_future_date(cls, v: str) -> str:
        date_obj = datetime.strptime(v, "%Y-%m-%d")
        if date_obj < datetime.now():
            raise ValueError("Cannot wager on past dates")
        return v
```


## Performance Guidelines

- **Database**: Use single joined queries; avoid N+1 patterns (don't query per-row inside a loop)
- **Model loading**: Cache loaded `.pkl` models in a module-level dict to avoid repeated disk I/O on each request


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

Comments should explain *why*, not *what*. If the comment restates what the code already says, delete it.


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



