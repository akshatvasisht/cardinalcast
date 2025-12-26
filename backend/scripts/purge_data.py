#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, select, delete
from backend.database import engine
from backend.models import Wager, WeatherForecast, WeatherSnapshot, Odds

RETENTION_DAYS = 365

def purge_old_data():
    cutoff_date = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
    cutoff_date_obj = cutoff_date.date()
    
    with Session(engine) as session:
        # Purge old Wagers
        stmt_wagers = delete(Wager).where(Wager.created_at < cutoff_date)
        res_wagers = session.exec(stmt_wagers)
        
        # Purge old WeatherForecasts
        stmt_forecasts = delete(WeatherForecast).where(WeatherForecast.created_at < cutoff_date)
        res_forecasts = session.exec(stmt_forecasts)

        # Purge old WeatherSnapshots
        stmt_snapshots = delete(WeatherSnapshot).where(WeatherSnapshot.created_at < cutoff_date)
        res_snapshots = session.exec(stmt_snapshots)

        # Purge old Odds
        stmt_odds = delete(Odds).where(Odds.created_at < cutoff_date)
        res_odds = session.exec(stmt_odds)

        session.commit()
        
        print(f"Purge complete for data older than {RETENTION_DAYS} days ({cutoff_date.isoformat()}).")
        print(f"Deleted Wagers: {res_wagers.rowcount}")
        print(f"Deleted WeatherForecasts: {res_forecasts.rowcount}")
        print(f"Deleted WeatherSnapshots: {res_snapshots.rowcount}")
        print(f"Deleted Odds: {res_odds.rowcount}")

if __name__ == "__main__":
    purge_old_data()
