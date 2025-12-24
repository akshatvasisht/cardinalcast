
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging
from scipy.stats import norm

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.odds_service import payout_logic, daily_tasks

CSV_PATH = _REPO_ROOT / "data" / "cleaned_weather_data.csv"

def analyze_calibration():
    df = pd.read_csv(CSV_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').tail(100) # Analyze last 100 days
    
    target = "high_temp"
    col = "high_temp"
    
    wins = 0
    total_prob = 0
    total_fair_ev = 0
    count = 0
    
    for i in range(40, len(df)):
        actual = df.iloc[i][col]
        # Prev Day Prediction
        p50 = df.iloc[i-1][col]
        # 30 day std
        std = df.iloc[i-30:i][col].std()
        
        # 3-day anchor for buckets
        anchor = df.iloc[i-3:i][col].mean()
        buckets = daily_tasks.generate_buckets_for_target(target, anchor)
        
        prediction = {
            "final_p10": p50 - (1.28 * std),
            "final_p50": p50,
            "final_p90": p50 + (1.28 * std)
        }
        
        priced = payout_logic.calculate_bucket_odds(prediction, buckets)
        fav = max(priced, key=lambda b: b["probability"])
        
        is_win = (actual >= fav["bucket_low"]) and (actual < fav["bucket_high"])
        if is_win: wins += 1
        
        total_prob += fav["probability"]
        count += 1
        
    print(f"Analysis for {target}:")
    print(f"  Observed Win Rate: {wins/count:.2f}")
    print(f"  Mean Predicted Prob: {total_prob/count:.2f}")
    print(f"  Delta (Calibration Error): {total_prob/count - wins/count:.2f}")
    print(f"  Average Std Dev: {df[col].tail(100).std():.2f}")

if __name__ == "__main__":
    analyze_calibration()
