"""
Feature Engineering Module for WindFall ML.

This module transforms raw weather data into engineered features that
improve ML model performance. It creates temporal features, rolling
statistics, lag features, and derived meteorological features.
"""

import pandas as pd
import numpy as np

# Latitude for Madison, Wisconsin (location of weather station)
# Used for calculating daylight hours based on solar position
HARDCODED_LATITUDE = 43.14069


def calculate_daylight_hours(df, latitude_deg):
    """
    Calculates daylight hours for each day based on latitude and day of year.
    
    Uses solar declination angle calculations to determine the number of
    daylight hours. This is a meteorological feature that helps models
    understand seasonal patterns and their effect on weather.
    
    Args:
        df: DataFrame containing a 'day_of_year' column (1-366).
        latitude_deg: Latitude in degrees (positive for Northern Hemisphere).
    
    Returns:
        pd.Series: Series of daylight hours for each day.
    """
    lat_rad = np.deg2rad(latitude_deg)
    day_of_year = df['day_of_year']
    
    # 23.44 degrees is the Earth's axial tilt (obliquity)
    # This determines how much the sun's path varies by season
    solar_declination = -np.deg2rad(23.44) * np.cos(
        # 365.24 is the average length of a year in days
        # 10 is an offset to align with the winter solstice
        2 * np.pi / 365.24 * (day_of_year + 10)
    )
    
    cos_hour_angle = -np.tan(lat_rad) * np.tan(solar_declination)
    # Clip to valid range for arccos function [-1, 1]
    cos_hour_angle = np.clip(cos_hour_angle, -1.0, 1.0)
    hour_angle = np.arccos(cos_hour_angle)
    
    # 15 degrees per hour is the Earth's rotation rate
    # Multiply by 2 because hour_angle is half the daylight period
    daylight_hours = 2 * (np.rad2deg(hour_angle) / 15)
    return daylight_hours


def engineer_features(df):
    """
    Engineers features from raw weather data for ML model training.
    
    This function creates a comprehensive set of features including:
    - Temporal features (day of year, month, day of week with cyclical encoding)
    - Rolling window statistics (3, 7, 14, 30 day averages/sums)
    - Lag features (1, 2, 3 day lags)
    - Derived meteorological features (wind components, temperature anomalies)
    - Interaction features (combinations of base features)
    
    Args:
        df: DataFrame with raw weather data including a 'date' column
            and weather metrics (high_temp, precipitation, etc.).
    
    Returns:
        pd.DataFrame: DataFrame with all engineered features added.
                     Missing values are forward-filled then back-filled.
    """
    df = df.copy()

    # Extract basic temporal features
    df['day_of_year'] = df['date'].dt.dayofyear
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    
    # Cyclical encoding for temporal features
    # 366.0 is the maximum day of year (accounts for leap years)
    # Sin/cos encoding allows models to understand cyclical patterns
    df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 366.0)
    df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 366.0)
    # 12.0 is the number of months in a year
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12.0)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12.0)
    
    # Calculate daylight hours if not already present
    if 'daylight_hours' not in df.columns:
        df['daylight_hours'] = calculate_daylight_hours(
            df, HARDCODED_LATITUDE
        )

    # Rolling window features
    # Windows: 3 days (short-term), 7 days (weekly), 14 days (bi-weekly),
    #          30 days (monthly patterns)
    windows = [3, 7, 14, 30]
    roll_cols = [
        'high_temp', 'low_temp', 'avg_temp', 'precip', 'snowfall',
        'avg_wind_speed'
    ]
    for w in windows:
        for col in roll_cols:
            if col in df.columns:
                # Shift by 1 to use past data (not including current day)
                shifted_col = df[col].shift(1)
                # For precipitation/snowfall, sum makes more sense than average
                if 'precip' in col or 'snowfall' in col:
                    df[f'{col}_last_{w}d_sum'] = shifted_col.rolling(
                        window=w, min_periods=1
                    ).sum()
                else:
                    # For temperature/wind, average captures trends better
                    df[f'{col}_last_{w}d_avg'] = shifted_col.rolling(
                        window=w, min_periods=1
                    ).mean()

    # Lag features: values from previous days
    # Lags: 1 day (yesterday), 2 days (day before), 3 days
    lags = [1, 2, 3]
    lagged_cols = [
        'high_temp', 'low_temp', 'avg_temp', 'precip', 'snowfall',
        'avg_wind_speed', 'wind_gust_2min', 'wind_dir_2min',
        'total_sunshine'
    ]
    for lag in lags:
        for col in lagged_cols:
            if col in df.columns:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)

    # Snow depth lag feature (only 1-day lag needed)
    if 'snow_depth' in df.columns:
        df['snow_depth_lag_1'] = df['snow_depth'].shift(1)

    # Wind component decomposition
    # Converts wind direction and speed into north/south and east/west components
    # This helps models understand wind patterns better than raw direction
    if ('wind_dir_2min_lag_1' in df.columns and
            'avg_wind_speed_lag_1' in df.columns):
        df['wind_dir_2min_lag_1'] = df['wind_dir_2min_lag_1'].fillna(0)
        df['avg_wind_speed_lag_1'] = df['avg_wind_speed_lag_1'].fillna(0)
        # Convert degrees to radians for trigonometric functions
        # 180.0 is the conversion factor (degrees to radians = π/180)
        wind_dir_rad = df['wind_dir_2min_lag_1'] * np.pi / 180
        df['north_wind_speed_lag_1'] = \
            df['avg_wind_speed_lag_1'] * np.sin(wind_dir_rad)
        df['west_wind_speed_lag_1'] = \
            df['avg_wind_speed_lag_1'] * np.cos(wind_dir_rad)
            
    # Gust factor: difference between gust and average wind speed
    # Indicates wind variability and storm intensity
    if ('wind_gust_2min_lag_1' in df.columns and
            'avg_wind_speed_lag_1' in df.columns):
        df['gust_factor_lag_1'] = \
            df['wind_gust_2min_lag_1'] - df['avg_wind_speed_lag_1']
            
    # Temperature anomaly: deviation from 30-day average
    # Captures unusual temperature patterns
    if ('avg_temp_lag_1' in df.columns and
            'avg_temp_last_30d_avg' in df.columns):
        df['temp_anomaly_lag_1'] = \
            df['avg_temp_lag_1'] - df['avg_temp_last_30d_avg'].shift(1)
            
    # Temperature range: difference between high and low
    # Indicates daily temperature variability
    if 'high_temp_lag_1' in df.columns and 'low_temp_lag_1' in df.columns:
        df['temp_range_lag_1'] = \
            df['high_temp_lag_1'] - df['low_temp_lag_1']
            
    # Binary indicator for snow on ground
    # 0 = no snow, 1 = snow present
    if 'snow_depth_lag_1' in df.columns:
        df['snow_on_ground_lag_1'] = (
            df['snow_depth_lag_1'] > 0
        ).astype(int)
        
    # Interaction features: combinations that may have predictive power
    # Temperature anomaly × snow on ground (cold anomalies with snow)
    if ('temp_anomaly_lag_1' in df.columns and
            'snow_on_ground_lag_1' in df.columns):
        df['anomaly_x_snow_ground'] = \
            df['temp_anomaly_lag_1'] * df['snow_on_ground_lag_1']
            
    # North wind × winter season (cold air from north in winter)
    if ('north_wind_speed_lag_1' in df.columns and
            'day_of_year_cos' in df.columns):
        df['north_wind_x_winter'] = \
            df['north_wind_speed_lag_1'] * df['day_of_year_cos']
            
    # Gust factor × average wind (high variability with high wind)
    if ('gust_factor_lag_1' in df.columns and
            'avg_wind_speed_lag_1' in df.columns):
        df['gust_x_avg_wind'] = \
            df['gust_factor_lag_1'] * df['avg_wind_speed_lag_1']
            
    # Temperature range × precipitation (high range with precipitation)
    if 'temp_range_lag_1' in df.columns and 'precip_lag_1' in df.columns:
        df['temp_range_x_precip'] = \
            df['temp_range_lag_1'] * (df['precip_lag_1'] > 0).astype(int)

    # Weather type codes (WT01-WT22) from NOAA
    # These are binary indicators for different weather conditions
    # Range 1-22 covers all standard weather type codes
    wt_cols = [f'WT{i:02d}' for i in range(1, 23)]
    for col in wt_cols:
        if col in df.columns:
            df[f'{col}_lag_1'] = df[col].shift(1)

    # Forward fill then back fill to handle missing values
    # This ensures no NaN values remain that would break model predictions
    df = df.ffill().bfill()
    return df.copy()