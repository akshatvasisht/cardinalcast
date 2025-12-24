"""
Model Training Module for WindFall ML Pipeline.

This module trains XGBoost models for weather prediction using:
- Recursive Feature Elimination with Cross-Validation (RFECV) for feature selection
- Optuna for hyperparameter optimization
- Quantile regression for P10, P50, P90 predictions
- Time series cross-validation to respect temporal ordering

The trained models are saved to the ml_api/models directory for use by the API.
"""

import pandas as pd
import joblib
import optuna
import xgboost as xgb
import logging
import feature_engineering
import json
import time
from pathlib import Path
from sklearn.feature_selection import RFECV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import make_scorer, mean_absolute_error, mean_squared_error
from optuna.integration import OptunaSearchCV
from math import sqrt

# Configuration
CLEAN_DATA_PATH = 'data/cleaned_weather_data.csv'
MODEL_OUTPUT_DIR = '../backend/odds_service/models'
METRICS_OUTPUT_DIR = 'metrics'

# Random seed for reproducibility
# 67 is an arbitrary but fixed value to ensure consistent results across runs
RANDOM_SEED = 67

# Number of splits for time series cross-validation
# 2 splits provides a good balance between validation robustness and training data size
N_SPLITS = 2

# Number of trials for Optuna hyperparameter search
# 1 trial balances search thoroughness with training time
# More trials would find better parameters but take longer
OPTUNA_N_TRIALS = 1

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Define targets and their properties
# Each target has a 'name' (used for file naming) and 'target_col' (column in data)
TARGETS_TO_TRAIN = [
    {'name': 'high_temp', 'target_col': 'high_temp'},
    {'name': 'avg_wind_speed', 'target_col': 'avg_wind_speed'},
    {'name': 'precipitation', 'target_col': 'precip'}
]

# Quantiles to train models for
# 0.1 = 10th percentile (P10, lower bound)
# 0.5 = 50th percentile (P50, median)
# 0.9 = 90th percentile (P90, upper bound)
QUANTILES = [0.1, 0.5, 0.9]

# Define base features (all features from engineering)
# This list is dynamically constructed to match the features created by
# feature_engineering.engineer_features()
BASE_FEATURE_COLS = [
    'day_of_year', 'month', 'day_of_week', 'day_of_year_sin',
    'day_of_year_cos', 'month_sin', 'month_cos', 'daylight_hours'
]

# Dynamically add rolling window features
# Windows: 3 days (short-term), 7 days (weekly), 14 days (bi-weekly),
#          30 days (monthly patterns)
windows = [3, 7, 14, 30]
roll_base = ['high_temp', 'low_temp', 'avg_temp', 'precip', 'snowfall',
             'avg_wind_speed']
for w in windows:
    for col in roll_base:
        # Precipitation and snowfall use sum (cumulative)
        if 'precip' in col or 'snowfall' in col:
            BASE_FEATURE_COLS.append(f'{col}_last_{w}d_sum')
        else:
            # Temperature and wind use average (trend)
            BASE_FEATURE_COLS.append(f'{col}_last_{w}d_avg')

# Dynamically add lag features
# Lags: 1 day (yesterday), 2 days, 3 days
lags = [1, 2, 3]
lag_base = ['high_temp', 'low_temp', 'avg_temp', 'precip', 'snowfall',
            'avg_wind_speed', 'wind_gust_2min', 'wind_dir_2min',
            'total_sunshine']
for lag in lags:
    for col in lag_base:
        BASE_FEATURE_COLS.append(f'{col}_lag_{lag}')

# Add derived and interaction features
BASE_FEATURE_COLS.extend([
    'snow_depth_lag_1', 'north_wind_speed_lag_1', 'west_wind_speed_lag_1',
    'gust_factor_lag_1', 'temp_anomaly_lag_1', 'temp_range_lag_1',
    'snow_on_ground_lag_1', 'anomaly_x_snow_ground', 'north_wind_x_winter',
    'gust_x_avg_wind', 'temp_range_x_precip'
])

# Add weather type code lag features (WT01-WT22)
# Range 1-22 covers all standard NOAA weather type codes
wt_cols = [f'WT{i:02d}_lag_1' for i in range(1, 23)]
BASE_FEATURE_COLS.extend(wt_cols)


def load_cleaned_data(filepath):
    """
    Loads cleaned weather data from CSV file.
    
    Reads the cleaned dataset that was produced by data_cleaning.py.
    The date column is automatically parsed as datetime.
    
    Args:
        filepath: Path to the cleaned weather data CSV file.
    
    Returns:
        pd.DataFrame: DataFrame containing cleaned weather data, or empty
                     DataFrame if file not found.
    """
    logging.info(f"Loading cleaned data from {filepath}...")
    try:
        df = pd.read_csv(filepath, parse_dates=['date'])
        logging.info(f"Loaded {len(df)} rows")
        return df
    except FileNotFoundError:
        logging.error(f"Clean data file not found at {filepath}")
        return pd.DataFrame()


def prepare_data(df, target_col):
    """
    Prepares feature matrix X and target vector y for model training.
    
    Filters the DataFrame to only include features that exist in the data,
    removes rows with missing values in target or features, and returns
    aligned feature and target arrays.
    
    Args:
        df: DataFrame with engineered features and target column.
        target_col: Name of the target column to predict.
    
    Returns:
        tuple: (X, y) where:
               - X: Feature matrix (DataFrame) with selected features
               - y: Target vector (Series) with target values
    """
    logging.info(f"Preparing data for target: {target_col}")
    
    # Keep only features that exist in the dataframe
    # Some features may not exist if certain columns were missing from raw data
    existing_features = [
        col for col in BASE_FEATURE_COLS if col in df.columns
    ]
    
    # Ensure no NaNs in target or features
    # Drop rows where target or any feature is missing
    df_clean = df.dropna(subset=[target_col] + existing_features)
    
    X = df_clean[existing_features]
    y = df_clean[target_col]
    
    # Align columns to be safe (ensures correct column order)
    X = X[existing_features]
    
    return X, y


def run_rfe_cv(X, y, target_name, model_dir):
    """
    Runs Recursive Feature Elimination with Cross-Validation (RFECV).
    
    RFECV selects the optimal subset of features by recursively removing
    the least important features and evaluating model performance using
    time series cross-validation. This reduces overfitting and improves
    model generalization.
    
    Args:
        X: Feature matrix (DataFrame).
        y: Target vector (Series).
        target_name: Name of the target (used for file naming).
        model_dir: Directory to save the RFECV selector.
    
    Returns:
        RFECV: Fitted RFECV selector that can transform features.
    """
    logging.info(f"Running RFECV for {target_name}...")
    
    # Time series cross-validation respects temporal ordering
    # Prevents data leakage by ensuring training data always comes before test data
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    
    # Use MAE (Mean Absolute Error) for feature selection
    # MAE is robust to outliers and appropriate for regression tasks
    mae_scorer = make_scorer(mean_absolute_error, greater_is_better=False)
    
    # Base model for RFE
    # Uses a simple XGBoost model with fixed hyperparameters
    # 10 estimators is sufficient for feature selection (not final model)
    estimator = xgb.XGBRegressor(
        objective='reg:squarederror',
        random_state=RANDOM_SEED,
        n_jobs=-1,  # Use all available CPU cores
        n_estimators=10,  # Small number for faster RFE computation
        learning_rate=0.1
    )
    
    rfecv = RFECV(
        estimator=estimator,
        step=1,  # Remove one feature at a time
        cv=tscv,  # Use time series cross-validation
        scoring=mae_scorer,
        min_features_to_select=10,  # Keep at least 10 features
        n_jobs=-1,  # Use all available CPU cores
        verbose=1
    )
    
    rfecv.fit(X, y)
    
    logging.info(
        f"RFECV for {target_name} complete. "
        f"Optimal features: {rfecv.n_features_}"
    )
    
    # Save the fitted RFECV object
    # This will be loaded by the API to transform features during prediction
    model_path = model_dir / f"{target_name}_rfecv.pkl"
    joblib.dump(rfecv, model_path)
    logging.info(f"Saved RFECV selector to {model_path}")
    
    return rfecv


def save_metrics(metrics_dict, metrics_dir):
    """
    Saves training metrics to a JSON file.

    Appends metrics to a timestamped JSON file for tracking model performance
    over time. Each training run creates a new entry with timestamp, target,
    quantile, MAE, RMSE, and model path.

    Args:
        metrics_dict: Dictionary containing metrics to save.
        metrics_dir: Directory to save metrics files.
    """
    metrics_file = metrics_dir / "training_metrics.json"

    # Load existing metrics if file exists
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            all_metrics = json.load(f)
    else:
        all_metrics = []

    # Append new metrics
    all_metrics.append(metrics_dict)

    # Save back to file
    with open(metrics_file, 'w') as f:
        json.dump(all_metrics, f, indent=2)

    logging.info(f"Saved metrics to {metrics_file}")


def run_optuna_tuning(X_rfe, y, target_name, quantile, model_dir, metrics_dir):
    """
    Runs Optuna hyperparameter optimization for a quantile regression model.

    Uses Optuna to search for optimal hyperparameters for an XGBoost quantile
    regression model. The model is trained to predict a specific quantile
    (P10, P50, or P90) of the target distribution.

    Args:
        X_rfe: Feature matrix after RFE transformation (reduced features).
        y: Target vector (Series).
        target_name: Name of the target (e.g., 'high_temp').
        quantile: Quantile to predict (0.1, 0.5, or 0.9).
        model_dir: Directory to save the trained model.
        metrics_dir: Directory to save training metrics.
    """
    p_name = f"p{int(quantile * 100)}"
    model_full_name = f"{target_name}_{p_name}"
    logging.info(f"Running Optuna search for {model_full_name}...")
    
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    
    # 1. Define the base estimator
    # Uses quantile regression objective to predict specific percentiles
    # tree_method='hist' uses histogram-based algorithm (faster than exact)
    base_model = xgb.XGBRegressor(
        objective='reg:quantileerror',
        quantile_alpha=quantile,  # Target quantile (0.1, 0.5, or 0.9)
        random_state=RANDOM_SEED,
        n_jobs=-1,  # Use all available CPU cores
        tree_method='hist'  # Faster training algorithm
    )

    # 2. Define the search space for Optuna
    # These ranges are based on XGBoost best practices and empirical testing
    param_distributions = {
        # Number of boosting rounds (trees)
        'n_estimators': optuna.distributions.IntDistribution(100, 1000),
        # Learning rate (step size shrinkage)
        # Log scale because learning rate has multiplicative effect
        'learning_rate': optuna.distributions.FloatDistribution(
            0.01, 0.3, log=True
        ),
        # Maximum depth of trees (controls model complexity)
        'max_depth': optuna.distributions.IntDistribution(3, 10),
        # Fraction of samples used for each tree (prevents overfitting)
        'subsample': optuna.distributions.FloatDistribution(0.6, 1.0),
        # Fraction of features used for each tree (feature sampling)
        'colsample_bytree': optuna.distributions.FloatDistribution(0.6, 1.0),
        # Minimum sum of instance weight needed in a child (regularization)
        'min_child_weight': optuna.distributions.IntDistribution(1, 10),
    }

    # 3. Create the OptunaSearchCV object
    # Combines Optuna's efficient search with sklearn's cross-validation
    optuna_search = OptunaSearchCV(
        estimator=base_model,
        param_distributions=param_distributions,
        n_trials=OPTUNA_N_TRIALS,  # Number of hyperparameter combinations to try
        cv=tscv,  # Time series cross-validation
        scoring='neg_mean_absolute_error',  # Maximize negative MAE (minimize MAE)
        random_state=RANDOM_SEED,
        verbose=0  # Suppress Optuna output
    )

    # 4. Run the search
    optuna_search.fit(X_rfe, y)

    # 5. Get the best model
    best_model = optuna_search.best_estimator_
    logging.info(
        f"Optuna search complete for {model_full_name}. "
        f"Best MAE: {optuna_search.best_score_:.4f}"
    )
    logging.info(f"Best params: {optuna_search.best_params_}")

    # 6. Save the best model
    # This model will be loaded by the API for predictions
    model_path = model_dir / f"{model_full_name}_model.pkl"
    joblib.dump(best_model, model_path)
    logging.info(f"Saved {model_full_name} model to {model_path}")

    # 7. Compute additional metrics on the full dataset
    # Get predictions on training data for metrics logging
    y_pred = best_model.predict(X_rfe)
    mae = mean_absolute_error(y, y_pred)
    mse = mean_squared_error(y, y_pred)
    rmse = sqrt(mse)

    # 8. Log metrics to JSON
    metrics_dict = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target": target_name,
        "quantile": f"p{int(quantile * 100)}",
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "best_cv_mae": round(-optuna_search.best_score_, 4),
        "n_features": X_rfe.shape[1],
        "n_samples": len(y),
        "best_params": optuna_search.best_params_,
        "model_path": str(model_path.relative_to(model_path.parent.parent))
    }
    save_metrics(metrics_dict, metrics_dir)
    logging.info(f"Metrics - MAE: {mae:.4f}, RMSE: {rmse:.4f}")


def main():
    """
    Main entry point for the model training pipeline.
    
    Orchestrates the complete training process for all targets and quantiles:
    1. Loads cleaned data
    2. Engineers features
    3. For each target:
       a. Prepares feature and target data
       b. Runs RFECV for feature selection
       c. Trains P10, P50, P90 quantile regression models
       d. Saves all models to ml_api/models directory
    
    This function should be run after data_cleaning.py to train all models
    needed by the ML API.
    """
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / CLEAN_DATA_PATH
    model_dir = base_dir / "backend" / "odds_service" / "models"
    metrics_dir = base_dir / "ml_training" / METRICS_OUTPUT_DIR

    # Ensure directories exist
    # Models are saved to backend/odds_service/models so the API can load them
    # Metrics are saved to ml_training/metrics for tracking performance
    model_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    df = load_cleaned_data(data_path)
    if df.empty:
        logging.error("Cannot proceed without data.")
        return
        
    logging.info("Running feature engineering on full dataset...")
    df_features = feature_engineering.engineer_features(df)
    
    # Train models for each target (high_temp, avg_wind_speed, precipitation)
    for target in TARGETS_TO_TRAIN:
        target_name = target['name']
        target_col = target['target_col']
        
        logging.info("\n" + "=" * 50)
        logging.info(f"Starting pipeline for target: {target_name}")
        
        # 1. Prepare data (X, y)
        # Extract features and target, remove missing values
        X, y = prepare_data(df_features, target_col)
        
        # 2. Run RFE-CV and save selector
        # Selects optimal feature subset and saves selector for API use
        rfecv_selector = run_rfe_cv(X, y, target_name, model_dir)
        
        # 3. Get the RFE-transformed feature set
        # Reduces features to only those selected by RFECV
        logging.info("Transforming features with RFE selector...")
        X_rfe = rfecv_selector.transform(X)
        
        # 4. Train P10, P50, P90 models on RFE features
        # Each quantile gets its own optimized model
        for q in QUANTILES:
            run_optuna_tuning(X_rfe, y, target_name, q, model_dir, metrics_dir)
            
        logging.info(f"Pipeline complete for target: {target_name}")
        logging.info("=" * 50 + "\n")

    logging.info("All model training complete.")


if __name__ == "__main__":
    main()