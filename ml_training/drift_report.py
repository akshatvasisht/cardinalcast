import os
import sys
import logging
from datetime import date, timedelta
import pandas as pd
import json
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.odds_service import db
from backend.odds_service import model_services
from backend.odds_service import feature_engineering
from backend.database import engine
from sqlmodel import Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TARGETS = ["high_temp", "avg_wind_speed", "precipitation"]
LOOKBACK_DAYS = 60
EVAL_WINDOW_DAYS = 30


def main():
    logger.info("Starting Drift Report generation...")

    # 1. Fetch historical data from DB (with CSV fallback)
    logger.info("Fetching recent weather data...")
    try:
        with Session(engine) as session:
            fetch_days = 40 + LOOKBACK_DAYS  # extra history for feature lag warmup
            history_df = db.fetch_recent_weather_data(session, days=fetch_days)
            logger.info(f"Loaded {len(history_df)} rows from DB.")
    except Exception as e:
        logger.warning(f"DB connection failed ({e}). Falling back to CSV.")
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned_weather_data.csv")
        if os.path.exists(csv_path):
            history_df = pd.read_csv(csv_path)
            history_df['date'] = pd.to_datetime(history_df['date'])
            logger.info(f"Loaded {len(history_df)} rows from CSV.")
        else:
            logger.error(f"No data found in DB or CSV ({csv_path}).")
            return

    if history_df.empty:
        logger.error("No historical data found.")
        return

    # 2. Engineer features on full history (lags, rolling windows, etc.)
    engineered_df = feature_engineering.engineer_features(history_df)

    # Restrict to evaluation window (last EVAL_WINDOW_DAYS days with known actuals)
    cutoff_date = pd.Timestamp(date.today() - timedelta(days=EVAL_WINDOW_DAYS))
    eval_df = engineered_df[engineered_df["date"] >= cutoff_date].copy()

    if eval_df.empty:
        logger.warning(f"No data in live window (since {cutoff_date.date()}). Using last {EVAL_WINDOW_DAYS} available days.")
        eval_df = engineered_df.sort_values("date").tail(EVAL_WINDOW_DAYS).copy()

    if eval_df.empty:
        logger.error("No data available for evaluation.")
        return

    # 3. Load models
    logger.info("Loading models...")
    try:
        models = model_services.load_models()
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return

    results = []

    # 4. Evaluate each target
    print(f"\n{'='*60}")
    print(f"DRIFT REPORT (Last {EVAL_WINDOW_DAYS} days)")
    print(f"{'='*60}")
    print(f"{'Target':<20} | {'MAE':<10} | {'Bias (Mean Err)':<15}")
    print(f"{'-'*60}")

    # Map model target names to dataframe column names
    target_col_map = {
        "high_temp": "high_temp",
        "avg_wind_speed": "avg_wind_speed",
        "precipitation": "precip",  # feature_engineering uses "precip" column
    }

    metrics_export = {}

    for target in TARGETS:
        if target not in models:
            logger.warning(f"No model loaded for target: {target}. Skipping.")
            continue

        actual_col = target_col_map.get(target, target)
        if actual_col not in eval_df.columns:
            logger.warning(f"Actual column '{actual_col}' not found in data. Skipping {target}.")
            continue

        target_models = models[target]
        rfecv = target_models["rfecv"]
        p50_model = target_models["p50"]

        # Align features to training schema
        feature_names = rfecv.feature_names_in_
        X = eval_df.reindex(columns=feature_names, fill_value=0)

        # Guard: if >50% of training features are missing in eval data,
        # the model will predict near-constant values — skip and warn.
        missing_features = [f for f in feature_names if f not in eval_df.columns]
        if len(missing_features) > len(feature_names) * 0.5:
            logger.warning(
                f"{target}: {len(missing_features)}/{len(feature_names)} features "
                f"missing in eval data (>50%). Skipping — metrics would be unreliable."
            )
            continue

        X_rfe = rfecv.transform(X)

        # Predict p50
        preds = p50_model.predict(X_rfe)
        if target == "precipitation":
            preds = np.maximum(0, preds)

        actuals = eval_df[actual_col].fillna(0).values

        # Metrics
        mae = mean_absolute_error(actuals, preds)
        mse = mean_squared_error(actuals, preds)
        rmse = np.sqrt(mse)
        bias = float(np.mean(preds - actuals))

        metrics_export[target] = {
            "mae": float(mae),
            "rmse": float(rmse),
            "bias": float(bias)
        }

        print(f"{target:<20} | {mae:<10.4f} | {rmse:<10.4f} | {bias:<15.4f}")

        for date_val, act, pred in zip(eval_df["date"], actuals, preds):
            results.append({
                "date": date_val,
                "target": target,
                "actual": act,
                "predicted": pred,
                "error": float(pred) - float(act),
                "abs_error": abs(float(pred) - float(act)),
            })

    print(f"{'='*60}\n")

    # 5. Save detailed CSV
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    
    report_path = os.path.join(data_dir, "drift_report.csv")
    pd.DataFrame(results).to_csv(report_path, index=False)
    logger.info(f"Report saved to {report_path}")

    # 6. Save Metrics JSON for Backtest/Production
    metrics_path = os.path.join(data_dir, "model_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics_export, f, indent=4)
    logger.info(f"Metrics saved to {metrics_path}")


if __name__ == "__main__":
    main()
