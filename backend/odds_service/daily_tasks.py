"""
Daily Tasks Module for CardinalCast.

This module contains functions for scheduled daily tasks such as:
- Resolving past wagers against actual weather data
- Generating new odds for upcoming forecast dates

These tasks are intended to be run by a scheduler (e.g., cron) on a daily basis.
"""

import pandas as pd
import logging
import math
from datetime import datetime, timedelta, date
from typing import List, Tuple

from backend.odds_service import db
from backend.odds_service import model_services
from backend.odds_service import payout_logic

logger = logging.getLogger(__name__)

# Central configuration for all pricing
# Defines the NOAA anchor columns for each weather target
# Buckets are now generated dynamically based on the anchor value
TARGETS_TO_PRICE = {
    "high_temp": {
        "anchor_col": "noaa_high_temp"
    },
    "avg_wind_speed": {
        "anchor_col": "noaa_avg_wind_speed"
    },
    "precipitation": {
        "anchor_col": "noaa_precip"
    }
}


def _normalize_wager_numeric_fields(wager: dict) -> dict:
    """
    Returns a shallow copy of wager with numeric fields coerced to float.
    
    This protects downstream payout logic from Decimal values returned
    by MySQL and ensures all arithmetic is done in float space.
    """
    numeric_keys = [
        "bucket_low",
        "bucket_high",
        "amount",
        "base_payout_multiplier",
        "jackpot_multiplier",
    ]
    normalized = dict(wager)
    for key in numeric_keys:
        value = normalized.get(key)
        if value is not None:
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                # Leave value as-is if it cannot be converted; let
                # payout_logic raise a clearer error if needed.
                pass
    return normalized


def generate_buckets_for_target(target: str, anchor: float) -> List[Tuple[float, float]]:
    """
    Generates betting buckets dynamically based on the NOAA anchor value.
    
    Buckets are centered around the anchor value to ensure relevant betting ranges
    that adapt to different seasons and weather conditions.
    
    Args:
        target: Weather target ("high_temp", "avg_wind_speed", or "precipitation")
        anchor: NOAA forecast anchor value (the median/expected value)
    
    Returns:
        List of tuples (low, high) where low is inclusive, high is exclusive
    """
    if target == "high_temp":
        # Temperature: Generate 5 buckets of 5°F width, centered on anchor
        # Start at floor((anchor - 10) / 5) * 5 to center around anchor
        # This ensures anchor is roughly in the middle of the 5 buckets
        start = math.floor((anchor - 10) / 5) * 5
        buckets = []
        for i in range(5):
            low = start + (i * 5)
            high = low + 5
            buckets.append((low, high))
        return buckets
    
    elif target == "avg_wind_speed":
        # Wind Speed: Generate 4 buckets of 5 mph width, centered on anchor (clamped at 0)
        # Start at max(0, floor((anchor - 5) / 5) * 5)
        start = max(0, math.floor((anchor - 5) / 5) * 5)
        buckets = []
        for i in range(4):
            low = start + (i * 5)
            high = low + 5
            buckets.append((low, high))
        return buckets
    
    elif target == "precipitation":
        # Precipitation: Conditional logic based on anchor value
        if anchor < 0.1:
            # Dry Forecast: Use fixed micro-buckets for very low precipitation
            return [(0, 0.01), (0.01, 0.1), (0.1, 0.25), (0.25, 0.5)]
        else:
            # Wet Forecast: Generate buckets of 0.25" width centered on anchor
            # Start at floor((anchor - 0.5) / 0.25) * 0.25, clamped at 0
            start = max(0.0, math.floor((anchor - 0.5) / 0.25) * 0.25)
            buckets = []
            # Generate 4 buckets of 0.25" width
            for i in range(4):
                low = start + (i * 0.25)
                high = low + 0.25
                buckets.append((low, high))
            return buckets
    
    else:
        raise ValueError(f"Unknown target: {target}")


def resolve_past_wagers(db_conn):
    """
    Fetches pending wagers and updates them based on actual weather.
    
    This function is called daily to resolve wagers from the previous day.
    It retrieves all pending wagers for yesterday's date, compares them
    against actual weather measurements, and updates the database with
    win/loss status and payout amounts.
    
    Args:
        db_conn: Database connection for querying wagers and weather data.
    """
    logger.info("Starting daily task: Resolving past wagers...")
    
    # Resolve all wagers with forecast_date before today
    # (today's actual weather may not be complete yet)
    today = date.today()
    
    for target in TARGETS_TO_PRICE.keys():
        logger.info(f"Resolving wagers for target: {target}")
        
        pending_wagers = db.fetch_pending_wagers(db_conn, today, target)
        if not pending_wagers:
            logger.info(f"No pending wagers found for {target}.")
            continue

        # Cache of actuals by forecast date to avoid repeated DB hits
        actual_cache = {}

        # Resolve each wager and collect results for batch update
        results_to_update = []
        for wager in pending_wagers:
            forecast_date = wager.get("forecast_date")
            if forecast_date not in actual_cache:
                actual_value = db.fetch_actual_weather_result(
                    db_conn, forecast_date, target
                )
                actual_cache[forecast_date] = actual_value
            else:
                actual_value = actual_cache[forecast_date]

            # Partial ingestion can leave metrics NULL; skip resolution
            # until data for this specific date/target arrives
            if actual_value is None or (
                isinstance(actual_value, float) and math.isnan(actual_value)
            ):
                logger.warning(
                    "Skipping resolution for target %s on %s due to missing actual data",
                    target,
                    forecast_date,
                )
                continue

            # Normalize wager numeric fields to float before resolution
            normalized_wager = _normalize_wager_numeric_fields(wager)
            status, winnings = payout_logic.resolve_wager(
                normalized_wager, float(actual_value)
            )
            results_to_update.append({
                "wager_id": wager['wager_id'],
                "status": status,
                "winnings": winnings,
                "customer_id": wager['customer_id'],
                "type": wager['type'],
                "date": wager['date']
            })
            logger.info(
                f"Wager {wager['wager_id']}: {status}, "
                f"Winnings: ${winnings:.2f}"
            )

        # Batch update all wager results in the database
        db.update_wager_status_batch(db_conn, results_to_update)
    
    logger.info("Finished: Resolving past wagers.")


def generate_new_odds(db_conn, models):
    """
    Generates new odds for all available NOAA forecast days.
    
    This function retrieves NOAA forecasts from the database and generates
    betting odds for each forecast date and weather target. The odds are
    calculated using ML models and stored in the database for retrieval
    by the API endpoints.
    
    Args:
        db_conn: Database connection for fetching forecasts and storing odds.
        models: Dictionary of loaded ML models (from model_services.load_models()).
    """
    logger.info("Starting daily task: Generating new odds...")

    forecasts_df = db.fetch_noaa_forecasts(db_conn)
    if forecasts_df.empty:
        logger.warning("No NOAA forecasts found. Cannot generate new odds.")
        return

    new_odds_to_store = []

    # Process each forecast date
    for _, forecast in forecasts_df.iterrows():
        # Generate odds for each weather target
        for target, config in TARGETS_TO_PRICE.items():
            
            # Get the NOAA anchor value for this target
            # This is the forecast value that will be used as the median
            noaa_anchor = forecast.get(config["anchor_col"])
            if noaa_anchor is None or pd.isna(noaa_anchor):
                # Skip if NOAA doesn't have a forecast for this target
                continue

            # Generate buckets dynamically based on the anchor value
            buckets = generate_buckets_for_target(target, float(noaa_anchor))
            
            # Generate the probability distribution using ML models
            distribution = model_services.get_odds_distribution(
                models=models,
                target=target,
                forecast_date=forecast['date'].date(),
                noaa_anchor=float(noaa_anchor),
                db_conn=db_conn
            )
            
            # Price each betting bucket based on the distribution
            priced_buckets = payout_logic.calculate_bucket_odds(
                final_dist=distribution,
                buckets_to_price=buckets
            )
            
            # Store each bucket's odds in the database
            for bucket in priced_buckets:
                new_odds_to_store.append((
                    forecast['date'],
                    target,
                    bucket['bucket_name'],
                    bucket['bucket_low'],
                    bucket['bucket_high'],
                    bucket['probability'],
                    bucket['base_payout_multiplier'],
                    bucket['jackpot_multiplier']
                ))

    # Batch insert all generated odds into the database
    db.store_new_odds_batch(db_conn, new_odds_to_store)
    
    logger.info(
        f"Finished: Generating {len(new_odds_to_store)} new odds buckets."
    )


def main():
    """
    Main entry point for the scheduled daily task.
    
    This function coordinates the daily tasks:
    1. Resolves past wagers from yesterday
    2. Generates new odds for upcoming forecast dates
    
    NOTE: Currently, model loading is commented out because models
    are loaded by the API server. In a production cron job setup,
    models would be loaded here or the task would be an API endpoint.
    
    This function is intended to be called by a scheduler (e.g., cron)
    once per day, typically in the early morning after actual weather
    data becomes available.
    """
    logger.info(f"--- Daily Job Started: {datetime.now()} ---")
    
    db_conn = None
    try:
        # Models are managed by the API server at startup; pass empty dict here
        # since this job path runs outside the API process context.
        models = {}
        
        db_conn = db.get_db_connection()
        
        # Resolve wagers from yesterday
        resolve_past_wagers(db_conn)
        
        # Generate new odds for upcoming forecasts
        # Commented out because it requires models to be loaded
        # generate_new_odds(db_conn, models)
        
    except Exception as e:
        logger.critical(f"FATAL ERROR in daily job: {e}")
    
    finally:
        if db_conn:
            # Connection cleanup is handled by the context manager
            # in database_connector.get_db_connection()
            pass
        logger.info(f"--- Daily Job Finished: {datetime.now()} ---")


if __name__ == "__main__":
    # This main block is for local testing
    # In production, these functions would be called by a scheduler (cron)
    # or exposed as API endpoints that can be triggered by a scheduler
    main()