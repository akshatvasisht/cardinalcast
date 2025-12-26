"""Wager resolution: determine WIN/LOSE and update credits."""

import math
from datetime import date

from backend.odds_service import db
from backend.odds_service import payout_logic

TARGETS = ["high_temp", "avg_wind_speed", "precipitation"]


def resolve_wagers():
    """Resolve all pending wagers with forecast_date < today using actual weather."""
    from backend.database import SessionLocal
    from backend.config import TARGETS
    
    with SessionLocal() as session:
        today = date.today()
        for target in TARGETS:
            pending = db.fetch_pending_wagers(session, today, target)
            if not pending:
                continue
            actual_cache = {}
            results_to_update = []
            for wager in pending:
                forecast_date = wager.get("forecast_date")
                if forecast_date not in actual_cache:
                    actual_cache[forecast_date] = db.fetch_actual_weather_result(
                        session, forecast_date, target
                    )
                actual_value = actual_cache[forecast_date]
                if actual_value is None or (
                    isinstance(actual_value, float) and math.isnan(actual_value)
                ):
                    # Actual NOAA data not yet available — promote to PENDING_DATA
                    # so the user can see their wager is awaiting data.
                    # The nightly resolution job will re-resolve once data arrives.
                    results_to_update.append({
                        "wager_id": wager["wager_id"],
                        "status": "PENDING_DATA",
                        "winnings": 0.0,
                        "customer_id": wager["customer_id"],
                        "type": wager.get("type", target),
                        "date": wager.get("date"),
                    })
                    continue
                numeric_keys = [
                    "bucket_low", "bucket_high", "amount",
                    "base_payout_multiplier", "jackpot_multiplier",
                    "predicted_value",
                ]
                normalized = dict(wager)
                for k in numeric_keys:
                    if normalized.get(k) is not None:
                        try:
                            normalized[k] = float(normalized[k])
                        except (TypeError, ValueError):
                            pass
                status = "LOSE"
                winnings = 0.0
                
                wager_kind = normalized.get("wager_kind", "BUCKET")

                if wager_kind == "BUCKET":
                    status, winnings = payout_logic.resolve_wager(
                        normalized, float(actual_value)
                    )
                elif wager_kind == "OVER_UNDER":
                    # Resolve Over/Under
                    direction = normalized.get("direction")
                    predicted_value = float(normalized.get("predicted_value", 0.0))
                    amount = float(normalized.get("amount", 0.0))
                    multiplier = float(normalized.get("base_payout_multiplier", 1.0))
                    
                    is_win = False
                    if direction == "OVER":
                        is_win = float(actual_value) > predicted_value
                    elif direction == "UNDER":
                        is_win = float(actual_value) < predicted_value
                    # NOTE: Tie (equal) is a LOSS for the user (House Wins).
                    
                    if is_win:
                        status = "WIN"
                        winnings = amount * multiplier
                else:
                    # Unknown kind, treat as lost or skip? treating as lose for safety
                    pass
                results_to_update.append({
                    "wager_id": wager["wager_id"],
                    "status": status,
                    "winnings": winnings,
                    "customer_id": wager["customer_id"],
                    "type": wager.get("type", target),
                    "date": wager.get("date"),
                })
            if results_to_update:
                db.update_wager_status_batch(session, results_to_update)
