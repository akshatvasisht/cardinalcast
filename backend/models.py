"""SQLModel schema for CardinalCast. Used by Alembic for migrations."""

from datetime import date as date_type, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class WagerStatus(str, Enum):
    PENDING = "PENDING"
    WIN = "WIN"
    LOSE = "LOSE"
    PENDING_DATA = "PENDING_DATA"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    credits_balance: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_daily_claim_date: Optional[date_type] = Field(default=None)


class Wager(SQLModel, table=True):
    __tablename__ = "wagers"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    amount: int  # credits wagered
    target_value: Optional[float] = None  # e.g. temperature threshold
    status: str = Field(default=WagerStatus.PENDING.value, index=True)  # PENDING / WIN / LOSE
    odds: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    forecast_date: Optional[date_type] = None
    target: Optional[str] = None
    bucket_low: Optional[float] = None
    bucket_high: Optional[float] = None
    base_payout_multiplier: Optional[float] = None
    jackpot_multiplier: Optional[float] = None
    winnings: Optional[float] = None
    
    # New fields for Over/Under
    wager_kind: str = Field(default="BUCKET")  # BUCKET or OVER_UNDER
    direction: Optional[str] = None  # OVER or UNDER
    predicted_value: Optional[float] = None  # The threshold for OVER/UNDER


class WeatherSnapshot(SQLModel, table=True):
    """Ingestion and resolution: date, location, and observed values for ML/resolution."""

    __tablename__ = "weather_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True)  # e.g. YYYY-MM-DD
    location: str = Field(index=True)
    temperature: Optional[float] = None
    wind_speed: Optional[float] = None
    precipitation: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WeatherForecast(SQLModel, table=True):
    __tablename__ = "weather_forecasts"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: date_type = Field(index=True)
    noaa_high_temp: Optional[float] = None
    noaa_avg_wind_speed: Optional[float] = None
    noaa_precip: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Odds(SQLModel, table=True):
    __tablename__ = "odds"

    id: Optional[int] = Field(default=None, primary_key=True)
    forecast_date: date_type = Field(index=True)
    target: str = Field(index=True)
    bucket_name: str = Field(default="")
    bucket_low: float = Field(default=0.0)
    bucket_high: float = Field(default=0.0)
    probability: Optional[float] = None
    base_payout_multiplier: float = Field(default=1.0)
    jackpot_multiplier: float = Field(default=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
