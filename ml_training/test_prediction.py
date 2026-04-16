"""
Model Testing Module for CardinalCast ML Training Pipeline.

This module provides a testing utility to validate trained models by making
predictions on historical data and comparing them against known actual values.
It loads trained models and tests them on a specific date from the cleaned dataset.

NOTE: This script is intended to be run from the 'ml_training' directory.
It loads the full cleaned dataset (which already has features engineered)
and runs the models on a single row to compare predictions against actual values.
"""

import pandas as pd
import joblib
import sys
from pathlib import Path
import warnings

# --- Configuration ---

# Default date to test (must be in the cleaned CSV file)
# Format: 'YYYY-MM-DD'
# This date must exist in the cleaned_weather_data.csv file
DEFAULT_DATE = '2023-05-25'

# Default target variable to predict
# Options: 'high_temp', 'avg_wind_speed', 'precipitation'
DEFAULT_TARGET = 'high_temp'

# --- Paths (repo root for data and backend models) ---
REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "backend" / "odds_service" / "models"
DATA_PATH = REPO_ROOT / "data" / "cleaned_weather_data.csv"


def test_prediction(target_date_str: str, target: str):
    """
    Loads models and data to make a single prediction for a historical day.
    
    This function tests the trained models by:
    1. Loading the cleaned dataset and finding the specified date
    2. Loading the trained models (RFECV selector and P10/P50/P90 models)
    3. Preparing features using the RFECV selector
    4. Making predictions for all three quantiles
    5. Comparing predictions against the known actual value
    
    Args:
        target_date_str: Date to test in 'YYYY-MM-DD' format (must be in dataset).
        target: Target variable to predict ('high_temp', 'avg_wind_speed', or
               'precipitation').
    
    Note:
        The date must exist in the cleaned_weather_data.csv file. This script
        only works for dates within the training dataset.
    """
    print(f"--- Model Test for {target_date_str} ---")
    print(f"Target Variable: {target}\n")

    # --- 1. Load Data ---
    try:
        df = pd.read_csv(DATA_PATH)
        df['date'] = pd.to_datetime(df['date'])
    except FileNotFoundError:
        print(f"ERROR: Data file not found at {DATA_PATH}")
        return

    # --- 2. Find Specific Day ---
    target_date = pd.to_datetime(target_date_str)
    df_day = df[df['date'] == target_date]

    if df_day.empty:
        print(f"ERROR: Date {target_date_str} not found in {DATA_PATH}.")
        print("\nNOTE: This test script only works for dates *within* the cleaned dataset.")
        return

    # Get the actual value from the dataset
    try:
        actual_value = df_day[target].values[0]
    except KeyError:
        print(f"ERROR: Target column '{target}' not in data.")
        return

    # --- 3. Load Models ---
    # Load all four model artifacts needed for prediction:
    # - RFECV selector (for feature transformation)
    # - P10, P50, P90 models (for quantile predictions)
    try:
        rfecv = joblib.load(MODEL_DIR / f"{target}_rfecv.pkl")
        p10_model = joblib.load(MODEL_DIR / f"{target}_p10_model.pkl")
        p50_model = joblib.load(MODEL_DIR / f"{target}_p50_model.pkl")
        p90_model = joblib.load(MODEL_DIR / f"{target}_p90_model.pkl")
    except FileNotFoundError as e:
        print(f"ERROR: Could not load models from {MODEL_DIR}. {e}")
        print("Have you run train_models.py and saved the models to ../ml_api/models/?")
        return

    # --- 4. Prepare Feature Row ---
    # Get the feature names the RFE-CV was trained on
    # This ensures we use the same features in the same order
    initial_feature_names = rfecv.feature_names_in_

    # Align the day's data to those features
    # .reindex() ensures all columns are present and in the right order
    # fill_value=0 handles any missing features (shouldn't happen with cleaned data)
    feature_row_aligned = df_day.reindex(columns=initial_feature_names, fill_value=0)

    # Use the fitted RFE-CV to select the final features
    # This transforms the feature vector to only include selected features
    feature_row_rfe = rfecv.transform(feature_row_aligned)

    # --- 5. Make Predictions ---
    pred_p10 = p10_model.predict(feature_row_rfe)[0]
    pred_p50 = p50_model.predict(feature_row_rfe)[0]
    pred_p90 = p90_model.predict(feature_row_rfe)[0]

    # --- 6. Show Results ---
    print("--- Prediction Results ---")
    print(f"  P10 (10th Percentile): {pred_p10:.2f}")
    print(f"  P50 (Median):        {pred_p50:.2f}")
    print(f"  P90 (90th Percentile): {pred_p90:.2f}")
    print("-" * 28)
    print(f"  ACTUAL VALUE:          {actual_value:.2f}")
    print("-" * 28)
    print(f"  Error (Actual - P50):  {actual_value - pred_p50:.2f}\n")

    # Check if actual value falls within the predicted range
    # A good model should have the actual value within P10-P90 range most of the time
    if actual_value < pred_p10 or actual_value > pred_p90:
        print("RESULT: The actual value fell OUTSIDE the P10-P90 range.")
    else:
        print("RESULT: The actual value fell INSIDE the P10-P90 range.")
    print("\nNOTE: This test script only works for dates *within* the cleaned dataset.")


if __name__ == "__main__":
    """
    Main entry point for model testing.
    
    Allows testing models via command line:
    - python test_prediction.py [date] [target]
    - date: Optional date in 'YYYY-MM-DD' format (default: DEFAULT_DATE)
    - target: Optional target variable (default: DEFAULT_TARGET)
    
    Example:
        python test_prediction.py 2023-05-25 high_temp
    """
    # Suppress warnings from scikit-learn/joblib
    # These warnings are typically about deprecated features and don't affect functionality
    warnings.filterwarnings("ignore", category=UserWarning)

    # Get date from command line, or use default
    # sys.argv[0] is the script name, sys.argv[1] is first argument
    if len(sys.argv) > 1:
        date_to_test = sys.argv[1]
    else:
        date_to_test = DEFAULT_DATE

    # Get target from command line, or use default
    # sys.argv[2] is second argument (target variable)
    if len(sys.argv) > 2:
        target_to_test = sys.argv[2]
    else:
        target_to_test = DEFAULT_TARGET

    test_prediction(date_to_test, target_to_test)