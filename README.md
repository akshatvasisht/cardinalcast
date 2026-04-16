<p align="center">
  <img
    width="200"
    alt="CardinalCast Logo"
    src="docs/images/logo-original.png"
  />
</p>

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)
![ML](https://img.shields.io/badge/ML-XGBoost-orange)
![License](https://img.shields.io/badge/License-MIT-green)


CardinalCast is a Madison prediction market that allows users to place wagers on weather outcomes and win credits based on NOAA weather data. This system leverages XGBoost quantile regression (P10/P50/P90) to generate dynamic odds distributions that account for prediction uncertainty and historical forecast errors, enabling risk-adjusted wagering on temperature, wind, and precipitation outcomes.

### Core Functionality
* **ML-Powered Pricing:** Generates dynamic probability distributions using historical forecast errors and risk-adjusted uncertainty.
* **Automated Data Pipeline:** Daily ingestion of NOAA actuals and forecasts for scheduled wager resolution.
* **Interactive Wagering Interface:** React/TypeScript dashboard with weather map visualization, bucket-based wagers, over/under betting, and live leaderboard tracking.

<details>
  <summary><b>View Screenshots</b></summary>
  <br>

| Dashboard | History |
| :---: | :---: |
| <img src="docs/images/dashboard.png" width="100%"> | <img src="docs/images/history.png" width="100%"> |

</details>


## Impact & Performance

* **ML Model Accuracy:** 4.35°F MAE (high temp) with 81–85% interval coverage on held-out test set
* **System Latency:** Sub-100ms API response times for odds generation and wager placement
## Documentation

* **[SETUP.md](docs/SETUP.md):** Installation, environment configuration, and startup instructions.
* **[ARCHITECTURE.md](docs/ARCHITECTURE.md):** System design, data flow, glossary, and design decisions.
* **[API.md](docs/API.md):** REST API endpoint reference and authentication.
* **[TESTING.md](docs/TESTING.md):** Testing guidelines and strategy.
* **[STYLE.md](docs/STYLE.md):** Coding standards, testing guidelines, and repository conventions.

## License

See **[LICENSE](LICENSE)** file for details.
