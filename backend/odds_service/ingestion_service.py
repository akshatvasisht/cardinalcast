"""
Ingestion Service Module for WindFall ML API.

This module handles fetching weather data from external NOAA APIs:
- NOAA CDO (Climate Data Online) for historical actuals
- NOAA NWS (National Weather Service) Grid API for forecasts

Data is fetched, transformed to appropriate units, and stored in the database.
"""

import os
import requests
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from backend.odds_service import db

logger = logging.getLogger(__name__)

# NOAA CDO API configuration
NOAA_CDO_BASE_URL = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"
NOAA_CDO_TOKEN = os.environ.get("NOAA_CDO_TOKEN", "")

# Madison, WI weather station ID (Dane County Regional Airport)
MADISON_STATION_ID = "GHCND:USW00014837"

# NOAA NWS Grid API configuration (no auth required)
NWS_BASE_URL = "https://api.weather.gov"
# Madison, WI grid coordinates: Office=MKX (Milwaukee), Grid=66,64
NWS_OFFICE = "MKX"
NWS_GRID_X = 66
NWS_GRID_Y = 64

# User-Agent required by NWS API
NWS_USER_AGENT = "(WindFall Weather Betting, contact@windfall.example)"


def _celsius_tenths_to_fahrenheit(tenths_celsius: float) -> float:
    """
    Converts temperature from tenths of degrees Celsius to Fahrenheit.
    
    NOAA CDO stores TMAX/TMIN in tenths of degrees Celsius.
    Formula: F = (C * 9/5) + 32
    
    Args:
        tenths_celsius: Temperature in tenths of degrees Celsius.
    
    Returns:
        float: Temperature in degrees Fahrenheit.
    """
    celsius = tenths_celsius / 10.0
    fahrenheit = (celsius * 9 / 5) + 32
    return round(fahrenheit, 1)


def _mps_tenths_to_mph(tenths_mps: float) -> float:
    """
    Converts wind speed from tenths of m/s to mph.
    
    NOAA CDO stores AWND in tenths of meters per second.
    1 m/s = 2.23694 mph
    
    Args:
        tenths_mps: Wind speed in tenths of meters per second.
    
    Returns:
        float: Wind speed in miles per hour.
    """
    mps = tenths_mps / 10.0
    mph = mps * 2.23694
    return round(mph, 1)


def _mm_tenths_to_inches(tenths_mm: float) -> float:
    """
    Converts precipitation from tenths of mm to inches.
    
    NOAA CDO stores PRCP in tenths of millimeters.
    1 inch = 25.4 mm
    
    Args:
        tenths_mm: Precipitation in tenths of millimeters.
    
    Returns:
        float: Precipitation in inches.
    """
    mm = tenths_mm / 10.0
    inches = mm / 25.4
    return round(inches, 3)


def fetch_actuals_from_cdo(
    start_date: date,
    end_date: date
) -> List[Dict]:
    """
    Fetches actual weather data from NOAA CDO API.
    
    Retrieves TMAX (high temp), AWND (avg wind), and PRCP (precipitation)
    for the specified date range from the Madison, WI weather station.
    
    Args:
        start_date: Start date for data retrieval.
        end_date: End date for data retrieval (inclusive).
    
    Returns:
        List[Dict]: List of daily weather records with keys:
                   - date: Date of observation
                   - high_temp: Max temperature in Fahrenheit
                   - avg_wind_speed: Average wind speed in mph
                   - precipitation: Precipitation in inches
    
    Raises:
        ValueError: If NOAA_CDO_TOKEN is not set.
        requests.RequestException: If API request fails.
    """
    if not NOAA_CDO_TOKEN:
        raise ValueError(
            "NOAA_CDO_TOKEN environment variable is required for CDO API"
        )
    
    headers = {
        "token": NOAA_CDO_TOKEN
    }
    
    params = {
        "datasetid": "GHCND",
        "stationid": MADISON_STATION_ID,
        "startdate": start_date.isoformat(),
        "enddate": end_date.isoformat(),
        "datatypeid": "TMAX,AWND,PRCP",
        "limit": 1000
    }
    
    logger.info(
        f"Fetching CDO actuals from {start_date} to {end_date}"
    )
    
    response = requests.get(
        NOAA_CDO_BASE_URL,
        headers=headers,
        params=params,
        timeout=30
    )
    response.raise_for_status()
    
    data = response.json()
    results = data.get("results", [])
    
    if not results:
        logger.warning("No data returned from NOAA CDO API")
        return []
    
    # Group results by date
    daily_data = {}
    for record in results:
        record_date = record["date"][:10]  # Extract YYYY-MM-DD
        if record_date not in daily_data:
            daily_data[record_date] = {}
        
        datatype = record["datatype"]
        value = record["value"]
        
        if datatype == "TMAX":
            daily_data[record_date]["high_temp"] = _celsius_tenths_to_fahrenheit(value)
        elif datatype == "AWND":
            daily_data[record_date]["avg_wind_speed"] = _mps_tenths_to_mph(value)
        elif datatype == "PRCP":
            daily_data[record_date]["precipitation"] = _mm_tenths_to_inches(value)
    
    # Convert to list format
    actuals = []
    for date_str, values in daily_data.items():
        # Store partial records; missing fields remain None and become NULL in SQL
        actuals.append({
            "date": datetime.strptime(date_str, "%Y-%m-%d").date(),
            "high_temp": values.get("high_temp"),
            "avg_wind_speed": values.get("avg_wind_speed"),
            "precipitation": values.get("precipitation")
        })
    
    logger.info(f"Fetched {len(actuals)} daily records from CDO (partial data allowed)")
    return actuals


def fetch_forecasts_from_nws() -> List[Dict]:
    """
    Fetches forecast data from NOAA NWS Grid API.
    
    Retrieves gridpoint forecast for Madison, WI with:
    - maxTemperature: Daily maximum temperature
    - quantitativePrecipitation: 24-hour precipitation sum
    - windSpeed: Average wind speed
    
    Returns:
        List[Dict]: List of daily forecast records with keys:
                   - date: Forecast date
                   - noaa_high_temp: Max temperature in Fahrenheit
                   - noaa_avg_wind_speed: Average wind speed in mph
                   - noaa_precip: Precipitation in inches
    
    Raises:
        requests.RequestException: If API request fails.
    """
    headers = {
        "User-Agent": NWS_USER_AGENT,
        "Accept": "application/geo+json"
    }
    
    # Fetch gridpoint data (contains hourly/detailed forecast data)
    gridpoint_url = (
        f"{NWS_BASE_URL}/gridpoints/{NWS_OFFICE}/{NWS_GRID_X},{NWS_GRID_Y}"
    )
    
    logger.info(f"Fetching NWS forecast from {gridpoint_url}")
    
    response = requests.get(gridpoint_url, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    properties = data.get("properties", {})
    
    # Extract forecast data
    forecasts = {}
    
    # Process maxTemperature
    max_temp_data = properties.get("maxTemperature", {}).get("values", [])
    for entry in max_temp_data:
        valid_time = entry.get("validTime", "")
        value = entry.get("value")
        if valid_time and value is not None:
            # Extract date from ISO 8601 format
            date_str = valid_time.split("T")[0]
            forecast_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Only include future dates (next 7 days)
            if date.today() <= forecast_date <= date.today() + timedelta(days=7):
                if forecast_date not in forecasts:
                    forecasts[forecast_date] = {}
                # NWS returns Celsius, convert to Fahrenheit
                temp_f = (value * 9 / 5) + 32
                forecasts[forecast_date]["noaa_high_temp"] = round(temp_f, 1)
    
    # Process quantitativePrecipitation (sum over 24h periods)
    precip_data = properties.get("quantitativePrecipitation", {}).get("values", [])
    for entry in precip_data:
        valid_time = entry.get("validTime", "")
        value = entry.get("value")
        if valid_time and value is not None:
            date_str = valid_time.split("T")[0]
            forecast_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            if date.today() <= forecast_date <= date.today() + timedelta(days=7):
                if forecast_date not in forecasts:
                    forecasts[forecast_date] = {}
                # NWS returns mm, convert to inches
                precip_inches = value / 25.4
                # Sum if multiple periods in same day
                current = forecasts[forecast_date].get("noaa_precip", 0)
                forecasts[forecast_date]["noaa_precip"] = round(current + precip_inches, 3)
    
    # Process windSpeed (average over 24h periods)
    wind_data = properties.get("windSpeed", {}).get("values", [])
    wind_counts = {}
    for entry in wind_data:
        valid_time = entry.get("validTime", "")
        value = entry.get("value")
        if valid_time and value is not None:
            date_str = valid_time.split("T")[0]
            forecast_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            if date.today() <= forecast_date <= date.today() + timedelta(days=7):
                if forecast_date not in forecasts:
                    forecasts[forecast_date] = {}
                # NWS returns km/h, convert to mph
                wind_mph = value * 0.621371
                # Running sum for averaging
                current = forecasts[forecast_date].get("noaa_avg_wind_speed", 0)
                forecasts[forecast_date]["noaa_avg_wind_speed"] = current + wind_mph
                wind_counts[forecast_date] = wind_counts.get(forecast_date, 0) + 1
    
    # Calculate wind averages
    for forecast_date in forecasts:
        if forecast_date in wind_counts and wind_counts[forecast_date] > 0:
            avg = forecasts[forecast_date]["noaa_avg_wind_speed"] / wind_counts[forecast_date]
            forecasts[forecast_date]["noaa_avg_wind_speed"] = round(avg, 1)
    
    # Convert to list format
    forecast_list = []
    for forecast_date, values in sorted(forecasts.items()):
        # Set defaults for missing values
        forecast_list.append({
            "date": forecast_date,
            "noaa_high_temp": values.get("noaa_high_temp"),
            "noaa_avg_wind_speed": values.get("noaa_avg_wind_speed"),
            "noaa_precip": values.get("noaa_precip", 0.0)
        })
    
    logger.info(f"Fetched {len(forecast_list)} days of NWS forecasts")
    return forecast_list


def ingest_recent_history(db_conn) -> int:
    """
    Ingests a recent history window of actual weather data from NOAA CDO.
    
    This \"wide net\" ingestion fetches a configurable lookback window of
    historical actuals (default 30 days) to automatically catch up on
    delayed NOAA updates. Existing rows are safely upserted in MySQL.
    
    Environment:
        NOAA_LOOKBACK_DAYS: Optional int, number of days to look back
                            from today (default: 30).
    
    Args:
        db_conn: Database connection for storing actuals.
    
    Returns:
        int: Number of daily records ingested for the lookback window.
    """
    lookback_days = int(os.environ.get("NOAA_LOOKBACK_DAYS", 30))
    if lookback_days <= 0:
        logger.warning(
            "NOAA_LOOKBACK_DAYS=%s is not positive; skipping ingestion.",
            lookback_days,
        )
        return 0

    today = date.today()
    end_date = today - timedelta(days=1)
    start_date = end_date - timedelta(days=lookback_days - 1)

    logger.info(
        "Ingesting recent history of actuals from %s to %s "
        "(lookback_days=%s)",
        start_date,
        end_date,
        lookback_days,
    )

    try:
        actuals = fetch_actuals_from_cdo(start_date, end_date)
        if actuals:
            db.store_weather_actuals(db_conn, actuals)
            logger.info(
                "Ingested %s days of actuals from %s to %s",
                len(actuals),
                start_date,
                end_date,
            )
            return len(actuals)
        else:
            logger.warning(
                "No actuals available from NOAA CDO for range %s to %s",
                start_date,
                end_date,
            )
            return 0
    except Exception as e:
        logger.error(f"Failed to ingest recent history of actuals: {e}")
        raise


def ingest_forecasts(db_conn) -> int:
    """
    Ingests forecast data from NOAA NWS Grid API.
    
    Fetches the next 7 days of forecasts and stores them in the
    database for odds generation.
    
    Args:
        db_conn: Database connection for storing forecasts.
    
    Returns:
        int: Number of forecast records ingested.
    """
    try:
        forecasts = fetch_forecasts_from_nws()
        if forecasts:
            db.store_noaa_forecasts(db_conn, forecasts)
            logger.info(f"Ingested {len(forecasts)} forecast records")
            return len(forecasts)
        else:
            logger.warning("No forecasts available from NWS")
            return 0
    except Exception as e:
        logger.error(f"Failed to ingest forecasts: {e}")
        raise


def backfill_actuals(db_conn, days: int = 30) -> int:
    """
    Backfills historical actual weather data from NOAA CDO.
    
    This function is intended for initial deployment or recovery
    scenarios where the database needs to be populated with
    historical data. It fetches the last N days of actuals.
    
    Args:
        db_conn: Database connection for storing actuals.
        days: Number of days to backfill (default: 30).
    
    Returns:
        int: Number of records ingested.
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    
    logger.info(f"Backfilling actuals from {start_date} to {end_date}")
    
    try:
        actuals = fetch_actuals_from_cdo(start_date, end_date)
        if actuals:
            db.store_weather_actuals(db_conn, actuals)
            logger.info(f"Backfilled {len(actuals)} days of actuals")
            return len(actuals)
        else:
            logger.warning("No historical data available for backfill")
            return 0
    except Exception as e:
        logger.error(f"Failed to backfill actuals: {e}")
        raise


def run_full_ingestion(db_conn) -> Dict[str, int]:
    """
    Runs the complete daily ingestion workflow.
    
    This is the main entry point for scheduled ingestion tasks.
    It ingests both actuals (for yesterday) and forecasts (for next 7 days).
    
    Args:
        db_conn: Database connection for storing data.
    
    Returns:
        Dict[str, int]: Dictionary with counts of ingested records:
                       - actuals_count: Number of actual records
                       - forecast_count: Number of forecast records
    """
    results = {
        "actuals_count": 0,
        "forecast_count": 0
    }
    
    # Ingest recent-history actuals with a wide lookback window
    try:
        results["actuals_count"] = ingest_recent_history(db_conn)
    except Exception as e:
        logger.error(f"Actuals ingestion failed: {e}")
    
    # Ingest forecasts
    try:
        results["forecast_count"] = ingest_forecasts(db_conn)
    except Exception as e:
        logger.error(f"Forecast ingestion failed: {e}")
    
    return results


