"""
Database adapter for CardinalCast ML service.
Uses SQLModel/SQLAlchemy Session and CardinalCast schema (PostgreSQL).
Replaces Windfall's MySQL database_connector.
"""

# Database adapter for CardinalCast ML service.
# Uses SQLModel/SQLAlchemy Session.
# Now expects an active Session object to be passed in.

import logging
from typing import List, Optional

import pandas as pd
from sqlalchemy import select
from sqlmodel import Session

from backend.models import (
    WeatherSnapshot,
    WeatherForecast,
    Odds,
    Wager,
    User,
)
from backend.config import DEFAULT_LOCATION

logger = logging.getLogger(__name__)


def fetch_recent_weather_data(session: Session, days: int = 90) -> pd.DataFrame:
    """
    Fetches the last N days of actual weather from weather_snapshots.
    Returns DataFrame with date, high_temp, avg_wind_speed, precipitation
    (ML feature engineering expects these column names).
    """
    stmt = (
        select(WeatherSnapshot)
        .where(WeatherSnapshot.location == DEFAULT_LOCATION)
        .order_by(WeatherSnapshot.date.desc())
        .limit(days)
    )
    rows = session.exec(stmt).all()
    if not rows:
        return pd.DataFrame(columns=["date", "high_temp", "avg_wind_speed", "precipitation"])
    data = [
        {
            "date": r.date,
            "high_temp": r.temperature,
            "avg_wind_speed": r.wind_speed,
            "precipitation": r.precipitation,
        }
        for r in reversed(rows)
    ]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["high_temp"] = pd.to_numeric(df["high_temp"], errors="coerce")
    df["avg_wind_speed"] = pd.to_numeric(df["avg_wind_speed"], errors="coerce")
    df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce")
    df["precip"] = df["precipitation"]  # ML feature_engineering expects 'precip'
    return df.sort_values(by="date")


def store_weather_actuals(session: Session, actuals: list) -> None:
    """Upsert weather actuals into weather_snapshots (date + location)."""
    if not actuals:
        return
    for a in actuals:
        d = a["date"]
        date_str = d.isoformat() if hasattr(d, "isoformat") else str(d)
        stmt = select(WeatherSnapshot).where(
            WeatherSnapshot.date == date_str,
            WeatherSnapshot.location == DEFAULT_LOCATION,
        )
        existing = session.exec(stmt).first()
        if existing is not None:
            existing.temperature = a.get("high_temp")
            existing.wind_speed = a.get("avg_wind_speed")
            existing.precipitation = a.get("precipitation")
        else:
            session.add(
                WeatherSnapshot(
                    date=date_str,
                    location=DEFAULT_LOCATION,
                    temperature=a.get("high_temp"),
                    wind_speed=a.get("avg_wind_speed"),
                    precipitation=a.get("precipitation"),
                )
            )
    session.commit()
    logger.info("Stored %s weather actual records", len(actuals))


def fetch_pending_wagers(session: Session, max_date, target: str) -> list:
    """Fetch pending wagers with forecast_date < max_date and target."""
    stmt = select(Wager).where(
        Wager.status.in_(["PENDING", "PENDING_DATA"]),
        Wager.forecast_date < max_date,
        Wager.target == target,
    )
    rows = session.exec(stmt).all()
    return [
        {
            "wager_id": r.id,
            "customer_id": r.user_id,
            "amount": float(r.amount),
            "bucket_low": r.bucket_low,
            "bucket_high": r.bucket_high,
            "base_payout_multiplier": r.base_payout_multiplier,
            "jackpot_multiplier": r.jackpot_multiplier,
            "forecast_date": r.forecast_date,
            "type": r.target or "",
            "date": r.forecast_date,
            "wager_kind": r.wager_kind,
            "direction": r.direction,
            "predicted_value": r.predicted_value,
        }
        for r in rows
    ]


def fetch_actual_weather_result(session: Session, result_date, target: str) -> float:
    """Get actual weather value for a date and target (column name)."""
    date_str = result_date.isoformat() if hasattr(result_date, "isoformat") else str(result_date)
    stmt = select(WeatherSnapshot).where(
        WeatherSnapshot.date == date_str,
        WeatherSnapshot.location == DEFAULT_LOCATION,
    )
    row = session.exec(stmt).first()
    if not row:
        return None
    if target == "high_temp":
        return float(row.temperature) if row.temperature is not None else None
    if target == "avg_wind_speed":
        return float(row.wind_speed) if row.wind_speed is not None else None
    if target == "precipitation":
        return float(row.precipitation) if row.precipitation is not None else None
    return None


def update_wager_status_batch(session: Session, results: list) -> None:
    """Update wager status and user credits (no customer_messages in scope)."""
    for r in results:
        wager = session.exec(select(Wager).where(Wager.id == r["wager_id"])).first()
        if not wager:
            continue
        wager.status = r["status"]
        wager.winnings = r["winnings"]
        from datetime import datetime

        wager.resolved_at = datetime.utcnow()
        if r["status"] == "WIN":
            # NOTE: Concurrency issue handled here? 
            # In batch job context, arguably less contention than user actions, 
            # but ideally we should lock if concurrent processing is possible.
            # For now, keeping as is, but daily_routes/wager_routes are critical paths.
            user = session.exec(select(User).where(User.id == r["customer_id"])).first()
            if user:
                user.credits_balance += int(round(r["winnings"]))
    session.commit()
    won = sum(1 for x in results if x.get("status") == "WIN")
    logger.info("Updated %s wager statuses (%s won)", len(results), won)


def store_new_odds_batch(session: Session, odds: list) -> None:
    """Insert or update odds buckets."""
    if not odds:
        return
    for row in odds:
        (forecast_date, target, bucket_name, bucket_low, bucket_high, prob, base_payout, jackpot) = row
        stmt = select(Odds).where(
            Odds.forecast_date == forecast_date,
            Odds.target == target,
            Odds.bucket_low == bucket_low,
            Odds.bucket_high == bucket_high,
        )
        existing = session.exec(stmt).first()
        if existing is not None:
            existing.probability = prob
            existing.base_payout_multiplier = base_payout
            existing.jackpot_multiplier = jackpot
        else:
            session.add(
                Odds(
                    forecast_date=forecast_date,
                    target=target,
                    bucket_name=bucket_name,
                    bucket_low=bucket_low,
                    bucket_high=bucket_high,
                    probability=prob,
                    base_payout_multiplier=base_payout,
                    jackpot_multiplier=jackpot,
                )
            )
    session.commit()
    logger.info("Stored %s odds buckets", len(odds))


def fetch_noaa_forecasts(session: Session) -> pd.DataFrame:
    """Fetch stored NOAA forecasts for dates >= today."""
    from datetime import date as date_type

    today = date_type.today()
    stmt = (
        select(WeatherForecast)
        .where(WeatherForecast.date >= today)
        .order_by(WeatherForecast.date)
    )
    rows = session.exec(stmt).all()
    if not rows:
        return pd.DataFrame(columns=["date", "noaa_high_temp", "noaa_avg_wind_speed", "noaa_precip"])
    data = [
        {
            "date": r.date,
            "noaa_high_temp": r.noaa_high_temp,
            "noaa_avg_wind_speed": r.noaa_avg_wind_speed,
            "noaa_precip": r.noaa_precip,
        }
        for r in rows
    ]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    return df


def store_noaa_forecasts(session: Session, forecasts: list) -> None:
    """Upsert NOAA forecast records."""
    if not forecasts:
        return
    for f in forecasts:
        d = f["date"]
        date_val = d if hasattr(d, "year") else pd.Timestamp(d).date()
        existing = session.exec(select(WeatherForecast).where(WeatherForecast.date == date_val)).first()
        if existing is not None:
            existing.noaa_high_temp = f.get("noaa_high_temp")
            existing.noaa_avg_wind_speed = f.get("noaa_avg_wind_speed")
            existing.noaa_precip = f.get("noaa_precip", 0.0)
        else:
            session.add(
                WeatherForecast(
                    date=date_val,
                    noaa_high_temp=f.get("noaa_high_temp"),
                    noaa_avg_wind_speed=f.get("noaa_avg_wind_speed"),
                    noaa_precip=f.get("noaa_precip", 0.0),
                )
            )
    session.commit()
    logger.info("Stored %s NOAA forecast records", len(forecasts))
