"""
API Schema Definitions for WindFall ML API.

This module defines all Pydantic models used for request/response validation
in the FastAPI endpoints. These schemas ensure type safety and data validation
for communication between the Spring Boot backend and the ML API.
"""

from pydantic import BaseModel, Field
from datetime import date
from typing import List


class OddsGenerationRequest(BaseModel):
    """
    Request schema for generating odds for a specific weather target.
    
    This is the JSON payload that the Spring Boot backend sends to request
    odds for one target (e.g., high_temp, precipitation, avg_wind_speed).
    
    Attributes:
        forecast_date: The date for which to generate odds predictions.
        noaa_anchor: The NOAA forecast value used as an anchor point for
                     the ML model's probability distribution.
        target: The weather metric being predicted (e.g., "high_temp",
                "precipitation", "avg_wind_speed").
    """
    forecast_date: date = Field(..., example="2025-11-10")
    noaa_anchor: float = Field(..., example=78.0)
    target: str = Field(..., example="high_temp")


class OddsBucket(BaseModel):
    """
    Represents a single payout bucket for weather predictions.
    
    A bucket defines a range of values (e.g., 75-80°F) that users can bet on.
    Each bucket has associated payout multipliers that determine winnings.
    
    Attributes:
        bucket_name: Human-readable name for the bucket (e.g., "75-80°F").
        bucket_low: Lower bound of the bucket range (inclusive).
        bucket_high: Upper bound of the bucket range (exclusive).
        probability: Estimated probability that the actual value falls
                     within this bucket (0.0 to 1.0).
        base_payout_multiplier: Base multiplier for winning bets in this bucket.
        jackpot_multiplier: Maximum multiplier for perfect predictions
                           (when actual value is at bucket center).
    """
    bucket_name: str = Field(..., example="75-80°F")
    bucket_low: float
    bucket_high: float
    probability: float = Field(..., example=0.25)
    base_payout_multiplier: float = Field(..., example=1.8)
    jackpot_multiplier: float = Field(..., example=3.5)


class OddsGenerationResponse(BaseModel):
    """
    Response schema containing generated odds and model predictions.
    
    This is the full JSON response that the ML API sends back to the
    Spring Boot backend after processing an odds generation request.
    
    Attributes:
        forecast_date: The date for which odds were generated.
        target: The weather metric that was predicted.
        noaa_anchor: The NOAA forecast value used as anchor.
        model_p10: 10th percentile prediction from the ML model.
        model_p50: 50th percentile (median) prediction from the ML model.
        model_p90: 90th percentile prediction from the ML model.
        risk_spread: Measure of uncertainty (p90 - p10).
        inaccuracy_multiplier: Risk multiplier applied based on forecast
                              distance (1.0, 1.5, or 2.0).
        buckets: List of priced betting buckets for this target.
    """
    forecast_date: date
    target: str
    noaa_anchor: float
    model_p10: float
    model_p50: float
    model_p90: float
    risk_spread: float
    inaccuracy_multiplier: float
    buckets: List[OddsBucket]


class Wager(BaseModel):
    """
    Represents a single wager placed by a user.
    
    This schema is used when resolving wagers against actual weather data.
    Each wager contains the betting information needed to calculate payouts.
    
    Attributes:
        wager_id: Unique identifier for the wager in the database.
        user_id: Identifier of the user who placed the wager.
        amount: Number of credits bet on this wager.
        bucket_low: Lower bound of the predicted range (inclusive).
        bucket_high: Upper bound of the predicted range (exclusive).
        base_payout_multiplier: Base payout multiplier for this bucket.
        jackpot_multiplier: Maximum payout multiplier for perfect predictions.
    """
    wager_id: int
    user_id: str
    amount: float
    bucket_low: float
    bucket_high: float
    base_payout_multiplier: float
    jackpot_multiplier: float


class WagerResolveRequest(BaseModel):
    """
    Request schema for resolving wagers against actual weather data.
    
    This is the JSON payload that the Spring Boot backend sends to resolve
    all pending wagers for a specific target using the actual weather value.
    
    Attributes:
        target: The weather metric being resolved (e.g., "high_temp").
        actual_value: The actual measured weather value for the target date.
        wagers: List of wagers to resolve against the actual value.
    """
    target: str = Field(..., example="high_temp")
    actual_value: float = Field(..., example=78.2)
    wagers: List[Wager]


class WagerResult(BaseModel):
    """
    Result of resolving a single wager.
    
    Contains the outcome and payout calculation for one wager after
    comparing the predicted range against the actual weather value.
    
    Attributes:
        wager_id: Unique identifier for the resolved wager.
        status: Resolution status ("WIN", "LOSE", or "ERROR").
        winnings: Number of credits won (0.0 if lost or error).
    """
    wager_id: int
    status: str = Field(..., example="WIN")
    winnings: float = Field(..., example=36.60)


class WagerResolveResponse(BaseModel):
    """
    Response schema containing results for all resolved wagers.
    
    This is the full JSON response that the ML API sends back to the
    Spring Boot backend after processing a wager resolution request.
    
    Attributes:
        results: List of resolution results for each wager.
    """
    results: List[WagerResult]