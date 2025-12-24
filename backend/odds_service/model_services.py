"""
Model services: load ML models and get odds distribution (CardinalCast, from Windfall).
"""

import joblib
import logging
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd

from backend.odds_service import feature_engineering
from backend.odds_service import db
from backend.odds_service.config import get_model_dir

logger = logging.getLogger(__name__)

MODEL_DIR_PATH = get_model_dir()
MODEL_TARGETS = ["high_temp", "avg_wind_speed", "precipitation"]
HISTORY_LOOKBACK_DAYS = 40
INACCURACY_MULTIPLIER_LOW = 1.5
INACCURACY_MULTIPLIER_HIGH = 2.0


def load_models() -> dict:
    logger.info("Loading all models from: %s", MODEL_DIR_PATH)
    models = {}
    for target in MODEL_TARGETS:
        models[target] = {}
        model_files = {
            "rfecv": MODEL_DIR_PATH / f"{target}_rfecv.pkl",
            "p10": MODEL_DIR_PATH / f"{target}_p10_model.pkl",
            "p50": MODEL_DIR_PATH / f"{target}_p50_model.pkl",
            "p90": MODEL_DIR_PATH / f"{target}_p90_model.pkl",
        }
        for name, path in model_files.items():
            if not path.exists():
                logger.error("Model file not found at %s", path)
                raise FileNotFoundError(f"Model file not found: {path}")
            with open(path, "rb") as f:
                models[target][name] = joblib.load(f)
    logger.info("All 12 model artifacts loaded successfully.")
    return models


def get_feature_row(forecast_date: date, history_df: pd.DataFrame) -> pd.DataFrame:
    placeholder_row = pd.DataFrame(columns=history_df.columns, index=[0])
    placeholder_row["date"] = pd.to_datetime(forecast_date)
    combined_df = pd.concat([history_df, placeholder_row], ignore_index=True)
    features_df = feature_engineering.engineer_features(combined_df)
    return features_df.iloc[[-1]]


def get_odds_distribution(
    models: dict, target: str, forecast_date: date, noaa_anchor: float, db_conn
) -> dict:
    if target not in models:
        raise ValueError(f"No models loaded for target: {target}")
    target_models = models[target]
    history_df = db.fetch_recent_weather_data(db_conn, days=HISTORY_LOOKBACK_DAYS)
    feature_row_df = get_feature_row(forecast_date, history_df)
    rfecv = target_models["rfecv"]
    initial_feature_names = rfecv.feature_names_in_
    feature_row_aligned = feature_row_df.reindex(
        columns=initial_feature_names, fill_value=0
    )
    feature_row_rfe = rfecv.transform(feature_row_aligned)
    your_p10 = target_models["p10"].predict(feature_row_rfe)[0]
    your_p50 = target_models["p50"].predict(feature_row_rfe)[0]
    your_p90 = target_models["p90"].predict(feature_row_rfe)[0]
    your_p50 = np.clip(your_p50, your_p10, your_p90)
    if target == "precipitation":
        your_p10 = max(0, your_p10)
        your_p50 = max(0, your_p50)
        your_p90 = max(0, your_p90)
    low_spread = your_p50 - your_p10
    high_spread = your_p90 - your_p50
    forecast_day_offset = (forecast_date - date.today()).days
    multiplier = 1.0
    if forecast_day_offset > 7:
        multiplier = INACCURACY_MULTIPLIER_HIGH
    elif forecast_day_offset > 3:
        multiplier = INACCURACY_MULTIPLIER_LOW
    final_low_spread = low_spread * multiplier
    final_high_spread = high_spread * multiplier
    final_p10 = noaa_anchor - final_low_spread
    final_p50 = noaa_anchor
    final_p90 = noaa_anchor + final_high_spread
    if target == "precipitation":
        final_p10 = max(0, final_p10)
        final_p50 = max(0, final_p50)
    return {
        "model_p10": float(your_p10),
        "model_p50": float(your_p50),
        "model_p90": float(your_p90),
        "risk_spread": float(your_p90 - your_p10),
        "inaccuracy_multiplier": multiplier,
        "final_p10": float(final_p10),
        "final_p50": float(final_p50),
        "final_p90": float(final_p90),
    }
