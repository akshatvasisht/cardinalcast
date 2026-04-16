# CardinalCast REST API

## Authentication

Protected routes require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via `POST /auth/register` or `POST /auth/login`.


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
{ "id": 1, "username": "alice", "credits_balance": 0, "last_daily_claim_date": "2025-02-15" }
```

**Errors:** `401` not authenticated or invalid token.


### Wagers

#### `POST /wagers`
Place a wager (requires Bearer token). Validates balance, resolves odds, creates wager, deducts credits.

Supports two wager kinds:

**Bucket wager** — predict that the actual value falls within a specific priced bucket:
```json
{
  "forecast_date": "2025-02-15",
  "target": "high_temp",
  "wager_kind": "BUCKET",
  "bucket_value": 77.5,
  "amount": 10
}
```

**Over/Under wager** — predict the actual value will be above or below a threshold:
```json
{
  "forecast_date": "2025-02-15",
  "target": "high_temp",
  "wager_kind": "OVER_UNDER",
  "direction": "OVER",
  "predicted_value": 75.0,
  "amount": 10
}
```

- `target`: one of `high_temp`, `avg_wind_speed`, `precipitation`
- `wager_kind`: `BUCKET` or `OVER_UNDER` (default: `BUCKET`)
- `bucket_value`: required for BUCKET — a value within the desired priced bucket for that date/target
- `direction`: required for OVER_UNDER — `OVER` or `UNDER`
- `predicted_value`: required for OVER_UNDER — the threshold value
- `amount`: credits to wager (must be positive, must not exceed balance)

**Response:** `201`
```json
{ "id": 1, "status": "PENDING", "message": "Wager placed" }
```

**Errors:** `400` insufficient credits, missing required fields, no odds/forecast for selection. `401` not authenticated.

#### `GET /wagers/preview`
Returns the estimated payout multiplier for a proposed Over/Under wager before placing it. **Requires Bearer token.**

**Query parameters:** `forecast_date`, `target`, `direction`, `predicted_value`

**Response:** `200`
```json
{ "multiplier": 1.85 }
```

#### `GET /wagers`
List the current user's wagers, newest first (requires Bearer token).

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
    "wager_kind": "BUCKET",
    "direction": null,
    "predicted_value": null,
    "base_payout_multiplier": 1.5,
    "winnings": null,
    "created_at": "2025-02-09T12:00:00"
  }
]
```


### Odds (wager options)

#### `GET /odds/dates`
List distinct forecast dates that have odds available. No auth required. Use to populate the date picker in the place-wager form.

**Response:** `200` — `Cache-Control: public, max-age=300`
```json
["2025-02-15", "2025-02-16", "2025-02-17"]
```


#### `GET /odds`
List available wager options (markets) from the Odds table. No auth required. Use for building the place-wager form (dropdowns for date, target, bucket). — `Cache-Control: public, max-age=300`

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


### Daily Credits

#### `GET /daily/status`
Check whether the current user can claim daily credits (requires Bearer token).

**Response:** `200`
```json
{ "status": "AVAILABLE" }
```
or
```json
{ "status": "CLAIMED" }
```

#### `POST /daily/claim`
Claim daily credits (+100) if available today (requires Bearer token). Idempotent per calendar day.

**Response:** `200`
```json
{
  "message": "Daily credits claimed successfully",
  "added_credits": 100,
  "new_balance": 200,
  "status": "CLAIMED"
}
```

**Errors:** `400` if already claimed today.


### Leaderboard

#### `GET /leaderboard/`
Get top users ranked by credits balance. Auth is optional — providing a Bearer token enables the `current_user` field so the authenticated user sees their rank even when they fall outside the top N.

**Query parameters:** `limit` (default: `10`, max: `50`)

**Response:** `200` — `Cache-Control: private, max-age=30`
```json
{
  "top": [
    { "username": "alice", "credits_balance": 540, "rank": 1 },
    { "username": "bob",   "credits_balance": 320, "rank": 2 }
  ],
  "current_user": { "username": "carol", "credits_balance": 80, "rank": 14 }
}
```

`current_user` is `null` when unauthenticated or when the authenticated user is already in `top`.


### Health

#### `GET /health`
**Response:** `200` `{ "status": "ok" }`


## OpenAPI

When the server is running, interactive docs are at `/docs` (Swagger UI) and `/redoc`.
