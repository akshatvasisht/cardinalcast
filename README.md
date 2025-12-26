<p align="center">
  <img
    width="400"
    alt="CardinalCast Logo"
    src="docs/images/logo-original.png"
  />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg?logo=react" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6.svg?logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/ML-XGBoost-orange.svg" alt="ML">
  <img src="https://img.shields.io/badge/Build-Passing-success.svg" alt="Build">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

## Overview

**CardinalCast** is a weather prediction wagering platform that allows users to place wagers on weather outcomes and win credits based on NOAA weather data. It is designed to demonstrate full-stack ML engineering by combining real-time weather data, quantile regression models, and interactive web interfaces.

Unlike traditional weather forecasting tools, this system leverages XGBoost quantile regression (P10/P50/P90) to generate dynamic odds distributions that account for prediction uncertainty and historical inaccuracy patterns, enabling risk-adjusted wagering on temperature, wind, and precipitation outcomes.

### Core Functionality
* **ML-Powered Odds Engine:** XGBoost models trained on NOAA historical data generate P10/P50/P90 distributions with risk adjustment for accurate probability-based pricing.
* **Real-Time Weather Integration:** Automated daily ingestion of NOAA observations and forecasts with scheduled wager resolution and credit payouts.
* **Interactive Wagering Interface:** React/TypeScript dashboard with weather map visualization, bucket-based wagers, over/under betting, and live leaderboard tracking.

<details>
  <summary><b>View Screenshots</b></summary>
  <br>

| Dashboard |
| :---: |
| <img src="docs/images/sidecar.png" width="100%"> |

</details>

---

## Impact & Performance

* **ML Model Accuracy:** P10/P50/P90 quantile regression with cross-validated MAE tracking (see [ml_training/metrics](ml_training/metrics/))
* **System Latency:** Sub-100ms API response times for odds generation and wager placement
* **Data Pipeline:** Automated daily NOAA data ingestion with scheduled resolution and leaderboard updates

## Testing

```bash
# Backend tests (pytest)
cd backend && pytest -v

# Frontend E2E tests (Playwright)
cd frontend && npm run test:e2e
```

**Coverage**: Demo-level testing showcasing capability. Production would include comprehensive unit tests (80%+ coverage), integration tests, and cross-browser E2E testing.

See [TESTING.md](docs/TESTING.md) for detailed testing strategy.

## Documentation

* **[SETUP.md](docs/SETUP.md):** Installation, environment configuration, and startup instructions.
* **[ARCHITECTURE.md](docs/ARCHITECTURE.md):** System design, data flow, glossary, and design decisions.
* **[API.md](docs/API.md):** REST API endpoint reference and authentication.
* **[TESTING.md](docs/TESTING.md):** Testing guidelines and strategy.
* **[STYLE.md](docs/STYLE.md):** Coding standards, testing guidelines, and repository conventions.

## License

See **[LICENSE](LICENSE)** file for details.
