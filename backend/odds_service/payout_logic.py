"""Payout and bucket odds logic."""

from typing import List, Dict, Tuple

import numpy as np
from scipy.stats import norm

from backend.config import (
    HOUSE_EDGE,
    MIN_PAYOUT_MULTIPLIER,
    MAX_PAYOUT_MULTIPLIER,
    MAX_JACKPOT_BONUS,
)


def _jackpot_tier_bonus(probability: float, base_payout: float) -> float:
    """Return jackpot multiplier based on probability tier."""
    if probability < 0.02:   # < 2% — ultra-rare
        tier_bonus = base_payout * 0.50
    elif probability < 0.05:  # < 5% — rare
        tier_bonus = base_payout * 0.35
    elif probability < 0.10:  # < 10% — uncommon
        tier_bonus = base_payout * 0.20
    else:                     # common
        tier_bonus = base_payout * 0.10
    return min(MAX_JACKPOT_BONUS, tier_bonus)


def calculate_bucket_probability(
    bucket_low: float, bucket_high: float, mean: float, std: float
) -> float:
    if std <= 0:
        if bucket_low <= mean < bucket_high:
            return 1.0
        return 0.0
    prob = norm.cdf(bucket_high, loc=mean, scale=std) - norm.cdf(
        bucket_low, loc=mean, scale=std
    )
    return max(0.001, min(0.999, prob))


def calculate_bucket_odds(
    final_dist: dict, buckets_to_price: List[Tuple[float, float]]
) -> List[Dict]:
    final_p10 = final_dist["final_p10"]
    final_p50 = final_dist["final_p50"]
    final_p90 = final_dist["final_p90"]
    
    # FACT-BASED CALIBRATION: Use derived RMSE (std_dev) if available
    rmse = final_dist.get("std_dev")
    if rmse and rmse > 0:
        estimated_std = float(rmse)
    else:
        # Fallback to spread estimation
        spread = final_p90 - final_p10
        estimated_std = spread / 2.56 if spread > 0 else 1.0

    priced_buckets = []
    bucket_probabilities = []
    total_expected_return = 0.0
    for (low, high) in buckets_to_price:
        probability = calculate_bucket_probability(
            bucket_low=low, bucket_high=high, mean=final_p50, std=estimated_std
        )
        bucket_probabilities.append((low, high, probability))
    prob_sum = sum(p for (_, _, p) in bucket_probabilities)
    normalization_factor = 1.0 / prob_sum if prob_sum > 0 else 1.0
    for (low, high, raw_prob) in bucket_probabilities:
        probability = raw_prob * normalization_factor
        fair_multiplier = 1.0 / probability if probability > 0 else 1.0
        base_payout = fair_multiplier * (1 - HOUSE_EDGE)
        
        # Clamp to bounds
        base_payout = max(
            MIN_PAYOUT_MULTIPLIER, min(MAX_PAYOUT_MULTIPLIER, base_payout)
        )
        
        jackpot_bonus = _jackpot_tier_bonus(probability, base_payout)
        jackpot_multiplier = base_payout + jackpot_bonus
        
        priced_buckets.append({
            "bucket_name": f"{low}-{high}",
            "bucket_low": low,
            "bucket_high": high,
            "probability": probability,
            "base_payout_multiplier": base_payout,
            "jackpot_multiplier": jackpot_multiplier,
        })

    # The previous scaling logic was mathematically unsound for single-bet fixed-odds.
    # We've removed it to allow correct (1/p * (1-edge)) payouts.
    
    for bucket in priced_buckets:
        bucket["probability"] = round(bucket["probability"], 4)
        bucket["base_payout_multiplier"] = round(
            bucket["base_payout_multiplier"], 2
        )
        bucket["jackpot_multiplier"] = round(bucket["jackpot_multiplier"], 2)
    return priced_buckets


def resolve_wager(wager: dict, actual_value: float) -> Tuple[str, float]:
    bucket_low = float(wager["bucket_low"])
    bucket_high = float(wager["bucket_high"])
    wager_amount = float(wager["amount"])
    base_payout = float(wager["base_payout_multiplier"])
    jackpot = float(wager["jackpot_multiplier"])
    actual_value = float(actual_value)
    is_win = (actual_value >= bucket_low) and (actual_value < bucket_high)
    if not is_win:
        return "LOSE", 0.0
    base_winnings = wager_amount * base_payout
    bucket_width = bucket_high - bucket_low
    if bucket_width <= 0:
        bucket_width = 1.0
    bullseye = bucket_low + (bucket_width / 2.0)
    max_distance = bucket_width / 2.0
    user_distance = abs(actual_value - bullseye)
    closeness_score = (max_distance - user_distance) / max_distance
    closeness_score = max(0.0, closeness_score)
    jackpot_winnings = (wager_amount * (jackpot - base_payout)) * closeness_score
    total_winnings = base_winnings + jackpot_winnings
    return "WIN", round(total_winnings, 2)


def calculate_over_under_multiplier(probability: float) -> float:
    """
    Calculate payout multiplier for Over/Under wagers.
    No jackpot, just base payout with house edge and clamping.
    """
    if probability <= 0:
        return 1.0  # Should not happen if prob is clamped, but fallback
    
    fair_multiplier = 1.0 / probability
    base_payout = fair_multiplier * (1 - HOUSE_EDGE)
    return round(
        max(MIN_PAYOUT_MULTIPLIER, min(MAX_PAYOUT_MULTIPLIER, base_payout)), 2
    )
