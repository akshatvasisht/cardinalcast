"""Data lifecycle management: purge old weather data to control DB size."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import Session, delete, select

from backend.models import WeatherForecast, WeatherSnapshot
from backend.database import SessionLocal

logger = logging.getLogger(__name__)


def purge_old_data(retention_days: int = 365):
    """
    Purge WeatherForecasts older than today and WeatherSnapshots older than retention_days.
    
    Args:
        retention_days: Number of days to keep snapshots (default 365 per plan).
    """
    try:
        with SessionLocal() as session:
            today = date.today()
            cutoff_snapshot = datetime.utcnow() - timedelta(days=retention_days)

            # 1. Delete old forecasts (where date < today)
            # Forecasts are relevant only for future/today; past forecasts are superseded by actuals in snapshots.
            stmt_forecast = delete(WeatherForecast).where(WeatherForecast.date < today)
            result_forecast = session.exec(stmt_forecast)
            deleted_forecasts = result_forecast.rowcount

            # 2. Delete old snapshots (where created_at < cutoff)
            # Snapshots are the historical "truth" for ML training, but we don't need infinite history.
            stmt_snapshot = delete(WeatherSnapshot).where(WeatherSnapshot.created_at < cutoff_snapshot)
            result_snapshot = session.exec(stmt_snapshot)
            deleted_snapshots = result_snapshot.rowcount

            session.commit()

            logger.info(
                "Data purge complete. Deleted %d old forecasts (< %s) and %d old snapshots (< %s days old).",
                deleted_forecasts,
                today,
                deleted_snapshots,
                retention_days,
            )

    except Exception as e:
        logger.exception("Failed to purge old data: %s", e)
