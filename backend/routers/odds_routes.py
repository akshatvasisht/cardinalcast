"""Read-only odds/markets for the frontend wager form."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Odds

router = APIRouter(prefix="/odds", tags=["odds"])


class OddsOption(BaseModel):
    id: int
    forecast_date: date
    target: str
    bucket_name: str
    bucket_low: float
    bucket_high: float
    probability: Optional[float]
    base_payout_multiplier: float
    jackpot_multiplier: float

    model_config = ConfigDict(from_attributes=True)


@router.get("/dates", response_model=List[str])
def get_odds_dates(
    db: Session = Depends(get_db),
):
    """
    Get a list of distinct dates for which odds exist.
    Used by the frontend calendar to highlight bettable days.
    """
    # Select distinct forecast_date from Odds
    stmt = select(Odds.forecast_date).distinct().order_by(Odds.forecast_date)
    dates = db.execute(stmt).scalars().all()
    return [d.isoformat() for d in dates]


@router.get("", response_model=List[dict])
def list_odds(
    response: Response,
    forecast_date: Optional[date] = Query(None, description="Filter by forecast date"),
    target: Optional[str] = Query(None, description="Filter by target (high_temp, avg_wind_speed, precipitation)"),
    db: Session = Depends(get_db),
):
    """List available wager options (markets) from the Odds table. No auth required."""
    # Odds are generated once daily — cache for 5 minutes in the browser.
    response.headers["Cache-Control"] = "public, max-age=300"
    q = select(Odds).order_by(Odds.forecast_date.asc(), Odds.target.asc(), Odds.bucket_low.asc())
    if forecast_date is not None:
        q = q.where(Odds.forecast_date == forecast_date)
    if target is not None:
        q = q.where(Odds.target == target)
    rows = db.execute(q).scalars().all()
    return [
        {
            "id": r.id,
            "forecast_date": r.forecast_date.isoformat(),
            "target": r.target,
            "bucket_name": r.bucket_name or "",
            "bucket_low": r.bucket_low,
            "bucket_high": r.bucket_high,
            "probability": r.probability,
            "base_payout_multiplier": r.base_payout_multiplier,
            "jackpot_multiplier": r.jackpot_multiplier,
        }
        for r in rows
    ]
