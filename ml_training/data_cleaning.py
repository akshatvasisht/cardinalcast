"""
Data Cleaning Module for CardinalCast ML Training Pipeline.

This module handles loading and cleaning raw weather data from NOAA.
It performs column renaming, data type conversion, missing value handling,
and filters data to a specific date range for model training.
"""

import pandas as pd
from pathlib import Path
import logging

# Configuration
# Raw data source: MADISON DANE CO REGIONAL AIRPORT, WI US (USW00014837) via NCEI NOAA
# This is the weather station identifier for Madison, Wisconsin
RAW_DATA_PATH = 'data/raw_weather_data.csv'
CLEAN_DATA_PATH = 'data/cleaned_weather_data.csv'

# Start date for data filtering
# 1940-01-01 ensures we have sufficient historical data for training
# while excluding very old data that may have quality issues
START_DATE = '1940-01-01'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def load_raw_data(filepath):
    """
    Loads raw weather data from a CSV file.
    
    Reads the NOAA weather data CSV file into a pandas DataFrame.
    Uses low_memory=False to ensure proper type inference for all columns.
    
    Args:
        filepath: Path to the raw weather data CSV file.
    
    Returns:
        pd.DataFrame: DataFrame containing raw weather data, or empty
                     DataFrame if file not found.
    """
    logging.info(f"Loading data from {filepath}...")
    try:
        df = pd.read_csv(filepath, low_memory=False)
        logging.info(f"Loaded {len(df)} rows")
        return df
    except FileNotFoundError:
        logging.error(f"Raw data file not found at {filepath}")
        return pd.DataFrame()


def clean_and_rename(df):
    """
    Cleans and renames weather data columns.
    
    Performs comprehensive data cleaning including:
    - Renaming NOAA column codes to human-readable names
    - Filtering to date range starting from START_DATE
    - Converting data types (dates, numeric)
    - Handling missing values with appropriate strategies:
      * Zero-fill for precipitation/snow/wind (can't be negative)
      * Forward/backward fill for temperatures/wind direction (continuous)
    
    Args:
        df: Raw DataFrame from NOAA with original column names.
    
    Returns:
        pd.DataFrame: Cleaned DataFrame with renamed columns, proper types,
                     and missing values handled.
    """
    logging.info("Cleaning and renaming columns...")
    
    # Map NOAA column codes to human-readable names
    # TMAX = maximum temperature, TMIN = minimum temperature, etc.
    rename_map = {
        'DATE': 'date', 'TMAX': 'high_temp', 'TMIN': 'low_temp',
        'TAVG': 'avg_temp', 'PRCP': 'precip', 'AWND': 'avg_wind_speed',
        'SNOW': 'snowfall', 'SNWD': 'snow_depth', 'WDF2': 'wind_dir_2min',
        'WDF5': 'wind_dir_5sec', 'WSF2': 'wind_gust_2min',
        'WSF5': 'wind_gust_5sec', 'TSUN': 'total_sunshine'
    }
    df = df.rename(columns=rename_map)

    # Select only the columns we need
    # base_cols: renamed weather metrics
    # wt_cols: weather type codes (WT01-WT22) from NOAA
    base_cols = [col for col in rename_map.values() if col in df.columns]
    wt_cols = [col for col in df.columns if 'WT' in col]
    df = df[base_cols + wt_cols]

    # Convert date column to datetime and filter by start date
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= START_DATE].copy()

    # Convert all numeric columns to numeric type
    # errors='coerce' converts invalid values to NaN
    numeric_cols = [col for col in df.columns if col != 'date']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Columns that should be filled with 0 for missing values
    # These represent quantities that can't be negative (precipitation, snow, etc.)
    fill_zero_cols = [
        'precip', 'snowfall', 'snow_depth', 'avg_wind_speed',
        'total_sunshine', 'wind_gust_2min', 'wind_gust_5sec'
    ] + wt_cols

    # Columns that should use forward/backward fill
    # These represent continuous measurements where missing values
    # are likely due to sensor issues, not actual zero values
    fill_ffill_cols = [
        'wind_dir_2min', 'wind_dir_5sec', 'high_temp', 'low_temp', 'avg_temp'
    ]

    # Fill missing values with 0 for quantity columns
    for col in fill_zero_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Fill missing values with forward/backward fill for continuous columns
    # Forward fill propagates last known value forward
    # Backward fill fills any remaining gaps from the next known value
    # Final fillna(0) handles edge cases where no data exists
    for col in fill_ffill_cols:
        if col in df.columns:
            df[col] = df[col].ffill()
            df[col] = df[col].bfill()
            df[col] = df[col].fillna(0)  # Final fallback

    logging.info(f"Data cleaned. {len(df)} rows remaining.")
    return df


def save_cleaned_data(df, filepath):
    """
    Saves cleaned data to a CSV file.
    
    Creates the output directory if it doesn't exist and writes the
    cleaned DataFrame to CSV format without the index.
    
    Args:
        df: Cleaned DataFrame to save.
        filepath: Path where the cleaned CSV file should be saved.
    """
    logging.info(f"Saving cleaned data to {filepath}...")
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    logging.info("Cleaned data saved successfully.")


def main():
    """
    Main entry point for the data cleaning pipeline.
    
    Orchestrates the complete data cleaning process:
    1. Loads raw weather data from CSV
    2. Cleans and renames columns
    3. Saves cleaned data to output CSV
    
    This function is intended to be run before model training to prepare
    the dataset for feature engineering and model training.
    """
    base_dir = Path(__file__).resolve().parent.parent
    raw_path = base_dir / RAW_DATA_PATH
    clean_path = base_dir / CLEAN_DATA_PATH

    raw_df = load_raw_data(raw_path)
    if not raw_df.empty:
        cleaned_df = clean_and_rename(raw_df)
        save_cleaned_data(cleaned_df, clean_path)
        logging.info("\nData cleaning pipeline complete.")
        logging.info(f"Final data shape: {cleaned_df.shape}")
        logging.info(cleaned_df.head())


if __name__ == "__main__":
    main()