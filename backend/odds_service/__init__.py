"""
CardinalCast ML service: odds distribution and bucket pricing facade.

Use get_odds() for odds distribution and get_priced_buckets() for placing wagers.
Models are loaded on first use or at app startup.
"""

__all__ = [
    "get_odds",
    "get_priced_buckets",
    "get_over_under_pricing",
    "load_models",
]

_models_cache = None


def load_models():
    """Load ML models (cached)."""
    global _models_cache
    if _models_cache is None:
        from backend.odds_service import model_services
        _models_cache = model_services.load_models()
    return _models_cache


def get_odds(forecast_date, target: str, noaa_anchor: float, db_conn=None):
    """
    Get risk-adjusted distribution (P10/P50/P90) for a target and date.
    Returns dict with model_p10, model_p50, model_p90, risk_spread,
    inaccuracy_multiplier, final_p10, final_p50, final_p90.
    """
    from backend.odds_service import model_services
    models = load_models()
    return model_services.get_odds_distribution(
        models=models,
        target=target,
        forecast_date=forecast_date,
        noaa_anchor=noaa_anchor,
        db_conn=db_conn,
    )


def get_priced_buckets(forecast_date, target: str, noaa_anchor: float, db_conn=None):
    """
    Get priced betting buckets for a target and date.
    Returns list of dicts with bucket_name, bucket_low, bucket_high,
    probability, base_payout_multiplier, jackpot_multiplier.
    """
    from backend.odds_service import daily_tasks, payout_logic

    distribution = get_odds(forecast_date, target, noaa_anchor, db_conn)
    buckets_to_price = daily_tasks.generate_buckets_for_target(target, noaa_anchor)
    return payout_logic.calculate_bucket_odds(
        final_dist=distribution,
        buckets_to_price=buckets_to_price,
    )


def get_over_under_pricing(forecast_date, target: str, threshold: float, direction: str, noaa_anchor: float, db_conn=None):
    """
    Get pricing (multiplier) for an Over/Under wager.
    """
    from backend.odds_service import payout_logic
    from scipy.stats import norm

    # 1. Get distribution
    dist = get_odds(forecast_date, target, noaa_anchor, db_conn)
    mean = dist["final_p50"]
    # Estimate sigma from p90-p10 spread (approx 2.56 sigma)
    spread = dist["final_p90"] - dist["final_p10"]
    sigma = spread / 2.56 if spread > 0 else 1.0

    # 2. accurate prob of Actual > Threshold
    # CDF(x) = prob(Actual <= x)
    prob_under = norm.cdf(threshold, loc=mean, scale=sigma)
    
    if direction.upper() == "OVER":
        probability = 1.0 - prob_under
    else:  # UNDER
        probability = prob_under
    
    # Clamp prob to reasonable bounds (e.g. 1% to 99%)
    probability = max(0.01, min(0.99, probability))

    # 3. Calculate multiplier
    return payout_logic.calculate_over_under_multiplier(probability)
