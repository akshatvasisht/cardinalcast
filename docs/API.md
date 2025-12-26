# CardinalCast REST API

## Authentication

Protected routes require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via `POST /auth/register` or `POST /auth/login`.

---

## Endpoints

### Auth

#### `POST /auth/register`
Register a new user and return a JWT.

**Request body:**
```json
{ "username": "alice", "password": "secret" }
```

**Response:** `200`
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

**Errors:** `400` if username already registered.

#### `POST /auth/login`
Authenticate and return a JWT.

**Request body:**
```json
{ "username": "alice", "password": "secret" }
```

**Response:** `200`
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

**Errors:** `401` invalid username or password.

#### `GET /auth/me`
Return current user (requires Bearer token).

**Response:** `200`
```json
{ "id": 1, "username": "alice", "credits_balance": 100 }
```

**Errors:** `401` not authenticated or invalid token.

---

### Wagers

#### `POST /wagers`
Place a wager (requires Bearer token). Validates balance, looks up odds for the selected bucket, creates wager, deducts credits.

**Request body:**
```json
{
  "forecast_date": "2025-02-15",
  "target": "high_temp",
  "bucket_value": 77.5,
  "amount": 10
}
```

- `target`: one of `high_temp`, `avg_wind_speed`, `precipitation`
- `bucket_value`: value that must fall within a priced bucket for that date/target
- `amount`: credits to wager

**Response:** `201`
```json
{ "id": 1, "status": "PENDING", "message": "Wager placed" }
```

**Errors:** `400` insufficient credits, no odds for selection, or invalid amount. `401` not authenticated.

#### `GET /wagers`
List the current user's wagers (requires Bearer token).

**Response:** `200`
```json
[
  {
    "id": 1,
    "amount": 10,
    "status": "PENDING",
    "forecast_date": "2025-02-15",
    "target": "high_temp",
    "bucket_low": 75.0,
    "bucket_high": 80.0,
    "created_at": "2025-02-09T12:00:00"
  }
]
```

---

### Odds (wager options)

#### `GET /odds`
List available wager options (markets) from the Odds table. No auth required. Use for building the place-wager form (e.g. dropdowns for date, target, bucket).

**Query parameters:**

| Parameter       | Type   | Required | Description                                                                 |
|----------------|--------|----------|-----------------------------------------------------------------------------|
| `forecast_date`| date   | No       | Filter by forecast date (YYYY-MM-DD).                                     |
| `target`       | string | No       | Filter by target: `high_temp`, `avg_wind_speed`, or `precipitation`.       |

**Response:** `200`
```json
[
  {
    "id": 1,
    "forecast_date": "2025-02-15",
    "target": "high_temp",
    "bucket_name": "70-75",
    "bucket_low": 70.0,
    "bucket_high": 75.0,
    "probability": 0.22,
    "base_payout_multiplier": 1.5,
    "jackpot_multiplier": 2.0
  }
]
```

---

### Health

#### `GET /health`
**Response:** `200` `{ "status": "ok" }`

---

## OpenAPI

When the server is running, interactive docs are at `/docs` (Swagger UI) and `/redoc`.
