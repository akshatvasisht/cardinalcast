from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Wager, Odds
from backend.auth import get_current_user
from backend.odds_service import db as ml_db

router = APIRouter(prefix="/wagers", tags=["wagers"])


class PlaceWagerRequest(BaseModel):
    forecast_date: date
    target: str  # high_temp, avg_wind_speed, precipitation
    amount: int
    # Bucket wager fields
    bucket_value: Optional[float] = None
    # Over/Under wager fields
    wager_kind: str = "BUCKET"  # BUCKET, OVER_UNDER
    direction: Optional[str] = None  # OVER, UNDER
    predicted_value: Optional[float] = None  # Threshold


class WagerResponse(BaseModel):
    id: int
    amount: int
    status: str
    forecast_date: Optional[date]
    target: Optional[str]
    bucket_low: Optional[float]
    bucket_high: Optional[float]
    wager_kind: str
    direction: Optional[str]
    predicted_value: Optional[float]
    created_at: datetime  # Changed to datetime

    class Config:
        from_attributes = True


@router.post("", status_code=201)
def place_wager(
    req: PlaceWagerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Lock user row to prevent race condition on balance check/deduction
    stmt = select(User).where(User.id == user.id).with_for_update()
    user_locked = db.exec(stmt).one()
    
    if user_locked.credits_balance < req.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient credits. You have {user_locked.credits_balance} but need {req.amount}",
        )

    # 1. Handle Bucket Wager
    if req.wager_kind == "BUCKET":
        if req.bucket_value is None:
            raise HTTPException(status_code=400, detail="Bucket value required for bucket wager")
        
        odds_row = (
            db.execute(
                select(Odds).where(
                    Odds.forecast_date == req.forecast_date,
                    Odds.target == req.target,
                    Odds.bucket_low <= req.bucket_value,
                    Odds.bucket_high > req.bucket_value,
                )
            )
            .scalars()
            .first()
        )
        if not odds_row:
            raise HTTPException(status_code=400, detail="No odds available for this selection")
        
        wager = Wager(
            user_id=user_locked.id,
            amount=req.amount,
            status="PENDING",
            forecast_date=req.forecast_date,
            target=req.target,
            wager_kind="BUCKET",
            bucket_low=odds_row.bucket_low,
            bucket_high=odds_row.bucket_high,
            base_payout_multiplier=odds_row.base_payout_multiplier,
            jackpot_multiplier=odds_row.jackpot_multiplier,
        )

    # 2. Handle Over/Under Wager
    elif req.wager_kind == "OVER_UNDER":
        if not req.direction or req.predicted_value is None:
            raise HTTPException(status_code=400, detail="Direction and predicted_value required for Over/Under")
        
        direction = req.direction.upper()
        if direction not in ["OVER", "UNDER"]:
            raise HTTPException(status_code=400, detail="Direction must be OVER or UNDER")
        
        from backend.models import WeatherForecast
        forecast = db.execute(
            select(WeatherForecast).where(WeatherForecast.date == req.forecast_date)
        ).scalars().first()
        
        if not forecast:
             raise HTTPException(status_code=400, detail="No forecast data available for this date")
        
        # Determine anchor based on target
        algo_anchor = 0.0
        if req.target == "high_temp":
            algo_anchor = forecast.noaa_high_temp
        elif req.target == "avg_wind_speed":
            algo_anchor = forecast.noaa_avg_wind_speed
        elif req.target == "precipitation":
            algo_anchor = forecast.noaa_precip
        
        if algo_anchor is None:
             raise HTTPException(status_code=400, detail="No anchor data for this target")

        from backend.odds_service import get_over_under_pricing
        multiplier = get_over_under_pricing(
            forecast_date=req.forecast_date,
            target=req.target,
            threshold=req.predicted_value,
            direction=direction,
            noaa_anchor=algo_anchor,
            db_conn=db,
        )
        
        wager = Wager(
            user_id=user_locked.id,
            amount=req.amount,
            status="PENDING",
            forecast_date=req.forecast_date,
            target=req.target,
            wager_kind="OVER_UNDER",
            direction=direction,
            predicted_value=req.predicted_value,
            base_payout_multiplier=multiplier,
            jackpot_multiplier=multiplier, # No jackpot for O/U
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid wager kind")

    db.add(wager)
    user_locked.credits_balance -= req.amount
    db.commit()
    db.refresh(wager)
    return {"id": wager.id, "status": "PENDING", "message": "Wager placed"}


@router.get("/preview")
def preview_over_under_multiplier(
    forecast_date: date,
    target: str,
    direction: str,
    predicted_value: float,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns the estimated multiplier for an Over/Under wager.
    Re-uses the exact same pricing logic as wager placement.
    """
    direction = direction.upper()
    if direction not in ["OVER", "UNDER"]:
        raise HTTPException(status_code=400, detail="Direction must be OVER or UNDER")
    
    from backend.models import WeatherForecast
    forecast = db.execute(
        select(WeatherForecast).where(WeatherForecast.date == forecast_date)
    ).scalars().first()
    
    if not forecast:
         raise HTTPException(status_code=400, detail="No forecast data available")
    
    # Determine anchor based on target
    algo_anchor = 0.0
    if target == "high_temp":
        algo_anchor = forecast.noaa_high_temp
    elif target == "avg_wind_speed":
        algo_anchor = forecast.noaa_avg_wind_speed
    elif target == "precipitation":
        algo_anchor = forecast.noaa_precip
    
    if algo_anchor is None:
         raise HTTPException(status_code=400, detail="No anchor data for this target")

    from backend.odds_service import get_over_under_pricing
    multiplier = get_over_under_pricing(
        forecast_date=forecast_date,
        target=target,
        threshold=predicted_value,
        direction=direction,
        noaa_anchor=algo_anchor,
        db_conn=db,
    )
    
    return {"multiplier": multiplier}


@router.get("", response_model=List[dict])
def list_wagers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.execute(select(Wager).where(Wager.user_id == user.id).order_by(Wager.created_at.desc())).scalars().all()
    return [
        {
            "id": r.id,
            "amount": r.amount,
            "status": r.status,
            "forecast_date": r.forecast_date.isoformat() if r.forecast_date else None,
            "target": r.target,
            "bucket_low": r.bucket_low,
            "bucket_high": r.bucket_high,
            "wager_kind": r.wager_kind,
            "direction": r.direction,
            "predicted_value": r.predicted_value,
            "winnings": r.winnings,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
