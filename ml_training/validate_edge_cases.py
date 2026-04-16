import sys
import os
import joblib
import pandas as pd
from pathlib import Path

# Add backend to path so we can import if needed, though this logic is standalone for now
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT))

from backend.odds_service.payout_logic import generate_buckets_pdf

MODEL_DIR = REPO_ROOT / "backend" / "odds_service" / "models"

def validate_edge_cases():
    """
    Validate the ML models against extreme edge case feature values
    and ensure the probability generation logic integrates to ~1.0.
    """
    print("--- Starting Edge Case Validation ---")
    
    # 1. Test Probability Summation Logic
    print("\n[1] Testing Probability Generation Summation")
    targets = ["high_temp", "avg_wind_speed", "precipitation"]
    for target in targets:
        # Mocking predictions for testing probability distribution
        # In a real scenario, these come from the ML predict output
        mock_p10 = 30.0 if target == "high_temp" else 2.0
        mock_p50 = 50.0 if target == "high_temp" else 5.0
        mock_p90 = 70.0 if target == "high_temp" else 10.0
        
        buckets = generate_buckets_pdf(target, mock_p10, mock_p50, mock_p90)
        
        prob_sum = sum(b.probability for b in buckets if b.probability is not None)
        print(f"  Target: {target:15} | Probability Sum: {prob_sum:.4f}")
        assert 0.99 <= prob_sum <= 1.01, f"Probabilities for {target} do not sum to 1.0! (Sum: {prob_sum})"

    # 2. Test Extreme Value Predictions (Model Stability)
    print("\n[2] Testing Model Stability on Extreme Features")
    target = "high_temp"
    
    try:
        rfecv = joblib.load(MODEL_DIR / f"{target}_rfecv.pkl")
        p10_model = joblib.load(MODEL_DIR / f"{target}_p10_model.pkl")
        p50_model = joblib.load(MODEL_DIR / f"{target}_p50_model.pkl")
        p90_model = joblib.load(MODEL_DIR / f"{target}_p90_model.pkl")
        
        features = rfecv.feature_names_in_
        
        # Create an artificial edge case row (e.g. extremely hot prior days, unusual seasonality)
        # We fill with 0s and artificially spike some likely features (like historical temps or day of year)
        df_edge = pd.DataFrame(0, index=[0], columns=features)
        
        # Spiking a generic feature if it exists in the selected set
        # This tests if the model explodes on unseen high values
        for col in df_edge.columns:
            if 'temp' in col.lower():
                df_edge.loc[0, col] = 50.0 # Extreme Celsius temp
        
        feature_row_rfe = rfecv.transform(df_edge)
        
        pred_p10 = p10_model.predict(feature_row_rfe)[0]
        pred_p50 = p50_model.predict(feature_row_rfe)[0]
        pred_p90 = p90_model.predict(feature_row_rfe)[0]
        
        print(f"  Extreme Input Result ({target}): P10={pred_p10:.2f} | P50={pred_p50:.2f} | P90={pred_p90:.2f}")
        
        # Verify quantiles hold their relationship
        assert pred_p10 <= pred_p50 <= pred_p90, "Quantile crossing detected in extreme edge case!"
        print("  Quantile relationship maintained.")
        
    except FileNotFoundError:
        print(f"  Models not found in {MODEL_DIR}. Skipping execution.")

    print("\nValidation script assertions passed!")

if __name__ == "__main__":
    validate_edge_cases()
