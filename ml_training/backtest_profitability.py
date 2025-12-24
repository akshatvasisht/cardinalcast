"""
Enhanced Backtest Profitability Script for CardinalCast.

This script validates that the house maintains profitability with
the current odds pricing strategy by simulating different bettor profiles.
"""

import sys
from pathlib import Path
from abc import ABC, abstractmethod
import random
import json

# Repo root on path so backend is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
import numpy as np
import logging
from datetime import date, timedelta

from backend.odds_service import feature_engineering, payout_logic, daily_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CSV_PATH = _REPO_ROOT / "data" / "cleaned_weather_data.csv"
BACKTEST_DAYS = 30
HISTORY_LOOKBACK = 40
BET_AMOUNT = 100.0

TARGETS_TO_TEST = {
    "high_temp": {"column": "high_temp"},
    "avg_wind_speed": {"column": "avg_wind_speed"},
    "precipitation": {"column": "precip"}
}

# --- Bettor Profiles ---

class Bettor(ABC):
    def __init__(self, name: str):
        self.name = name
        self.total_wagered = 0.0
        self.total_winnings = 0.0
        self.bets_placed = 0
        self.wins = 0

    @abstractmethod
    def select_bucket(self, priced_buckets: list) -> dict:
        pass

    def record_bet(self, wagered: float, winnings: float, won: bool):
        self.total_wagered += wagered
        self.total_winnings += winnings
        self.bets_placed += 1
        if won:
            self.wins += 1

class FavoriteBettor(Bettor):
    """Bets on the highest-probability bucket regardless of price."""
    def select_bucket(self, priced_buckets: list) -> dict:
        return max(priced_buckets, key=lambda b: b["probability"])

class RandomBettor(Bettor):
    """Bets on a random bucket. Statistically should lose exactly the House Edge."""
    def select_bucket(self, priced_buckets: list) -> dict:
        return random.choice(priced_buckets)

class SharpBettor(Bettor):
    """Only bets if the payout reflects a fair value or better (EV >= 1.0)."""
    def select_bucket(self, priced_buckets: list) -> dict:
        # Sort by EV descending
        ev_buckets = []
        for b in priced_buckets:
            # We use base_payout_multiplier for fairness check
            ev = b["probability"] * b["base_payout_multiplier"]
            if ev >= 0.98: # Sharp might bet on near-fair or better
                ev_buckets.append((ev, b))
        
        if not ev_buckets:
            return None
        return max(ev_buckets, key=lambda x: x[0])[1]

# --- Simulation Logic ---

def load_training_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Training data not found at {CSV_PATH}.")
    df = pd.read_csv(CSV_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').tail(BACKTEST_DAYS + HISTORY_LOOKBACK)
    return df.reset_index(drop=True)

def load_metrics():
    path = _REPO_ROOT / "data" / "model_metrics.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    print("WARNING: model_metrics.json not found. Backtest will use fallback variance.")
    return {}

def simulate_model_prediction(history_df: pd.DataFrame, target_day_idx: int, target: str, metrics: dict = None) -> dict:
    """
    Simulates model prediction with fact-based uncertainty (RMSE) if available.
    """
    column = TARGETS_TO_TEST[target]["column"]
    start_idx = max(0, target_day_idx - 30)
    historical_values = history_df.iloc[start_idx:target_day_idx][column].dropna()
    
    if len(historical_values) < 10:
        return {"final_p10": 0, "final_p50": 0, "final_p90": 0, "std_dev": 0}

    # FACT-BASED CALIBRATION: Use RMSE if available
    rmse = None
    if metrics and target in metrics:
        rmse = metrics[target].get("rmse")
    
    if rmse:
        std_dev = rmse
    else:
        # Fallback to historical std (no arbitrary multiplier)
        std_dev = historical_values.std() 
    
    if target_day_idx > 0:
        noaa_anchor = history_df.iloc[target_day_idx - 1][column]
    else:
        noaa_anchor = historical_values.mean()

    # Expand range using PDF logic (1.96 sigma for 95% CI is fair)
    final_p10 = noaa_anchor - (1.96 * std_dev) 
    final_p50 = noaa_anchor
    final_p90 = noaa_anchor + (1.96 * std_dev)

    if target == "precipitation":
        final_p10 = max(0, final_p10)
        final_p50 = max(0, final_p50)

    return {
        "final_p10": float(final_p10),
        "final_p50": float(final_p50),
        "final_p90": float(final_p90),
        "std_dev": float(std_dev)
    }

def find_matching_bucket(actual_value: float, buckets: list) -> tuple:
    for (low, high) in buckets:
        if low <= actual_value < high:
            return (low, high)
    return None

def run_enhanced_backtest():
    df = load_training_data()
    metrics = load_metrics()
    
    # No engineer_features needed for this simple sim, but keeping for consistency if added later
    
    bettors = [
        FavoriteBettor("The Favorite Bot (Dumb)"),
        RandomBettor("The Gambler (Random)"),
        SharpBettor("The Sharp (Value Only)")
    ]

    test_start_idx = len(df) - BACKTEST_DAYS

    for i in range(test_start_idx, len(df)):
        for target, config in TARGETS_TO_TEST.items():
            actual_value = df.iloc[i][config["column"]]
            if pd.isna(actual_value): continue

            # Dynamic Buckets
            history_start_idx = max(0, i - 3)
            history_window = df.iloc[history_start_idx:i][config["column"]].dropna()
            anchor = float(history_window.mean()) if len(history_window) > 0 else float(actual_value)
            buckets = daily_tasks.generate_buckets_for_target(target, anchor)

            # Pricing
            prediction = simulate_model_prediction(df, i, target, metrics=metrics)
            if prediction["final_p50"] == 0: continue
            priced_buckets = payout_logic.calculate_bucket_odds(prediction, buckets)

            # Let each bettor choose
            for bettor in bettors:
                choice = bettor.select_bucket(priced_buckets)
                if choice:
                    wager = {
                        "bucket_low": choice["bucket_low"],
                        "bucket_high": choice["bucket_high"],
                        "amount": BET_AMOUNT,
                        "base_payout_multiplier": choice["base_payout_multiplier"],
                        "jackpot_multiplier": choice["jackpot_multiplier"]
                    }
                    # Resolve against actual_value (outside buckets = LOSE)
                    status, winnings = payout_logic.resolve_wager(wager, actual_value)
                    bettor.record_bet(BET_AMOUNT, winnings, status == "WIN")

    return bettors

def print_enhanced_results(bettors: list):
    print("\n" + "=" * 70)
    print("CARDINALCAST ENHANCED BACKTEST (30 DAYS)")
    print("=" * 70)
    print(f"House Edge Setting: {payout_logic.HOUSE_EDGE * 100:.1f}%")
    
    print(f"{'Bettor Profile':<30} | {'Bets':<5} | {'Win %':<6} | {'Profit':<10} | {'Margin':<8}")
    print("-" * 70)
    
    for b in bettors:
        win_rate = (b.wins / b.bets_placed * 100) if b.bets_placed > 0 else 0
        profit = b.total_winnings - b.total_wagered
        margin = (profit / b.total_wagered * 100) if b.total_wagered > 0 else 0
        
        # We show margin from HOUSE perspective, so flip the sign
        house_margin = -margin 
        
        print(f"{b.name:<30} | {b.bets_placed:<5} | {win_rate:>5.1f}% | {(-profit):>10.2f} | {house_margin:>7.1f}%")

    print("=" * 70)
    print("Note: House Margin should ideally converge to 10.0% for 'The Gambler'.")

if __name__ == "__main__":
    results = run_enhanced_backtest()
    print_enhanced_results(results)
