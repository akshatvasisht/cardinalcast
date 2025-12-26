"""Phase 2: wager bucket fields, weather_snapshots.precipitation, weather_forecasts, odds.

Revision ID: 002
Revises: 001
Create Date: 2025-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("wagers", sa.Column("forecast_date", sa.Date(), nullable=True))
    op.add_column("wagers", sa.Column("target", sa.String(), nullable=True))
    op.add_column("wagers", sa.Column("bucket_low", sa.Float(), nullable=True))
    op.add_column("wagers", sa.Column("bucket_high", sa.Float(), nullable=True))
    op.add_column("wagers", sa.Column("base_payout_multiplier", sa.Float(), nullable=True))
    op.add_column("wagers", sa.Column("jackpot_multiplier", sa.Float(), nullable=True))
    op.add_column("wagers", sa.Column("winnings", sa.Float(), nullable=True))

    op.add_column("weather_snapshots", sa.Column("precipitation", sa.Float(), nullable=True))

    op.create_table(
        "weather_forecasts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("noaa_high_temp", sa.Float(), nullable=True),
        sa.Column("noaa_avg_wind_speed", sa.Float(), nullable=True),
        sa.Column("noaa_precip", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_weather_forecasts_date", "weather_forecasts", ["date"], unique=False)

    op.create_table(
        "odds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("bucket_name", sa.String(), nullable=False, server_default=""),
        sa.Column("bucket_low", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bucket_high", sa.Float(), nullable=False, server_default="0"),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("base_payout_multiplier", sa.Float(), nullable=False, server_default="1"),
        sa.Column("jackpot_multiplier", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_odds_forecast_date", "odds", ["forecast_date"], unique=False)
    op.create_index("ix_odds_target", "odds", ["target"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_odds_target", "odds")
    op.drop_index("ix_odds_forecast_date", "odds")
    op.drop_table("odds")
    op.drop_index("ix_weather_forecasts_date", "weather_forecasts")
    op.drop_table("weather_forecasts")
    op.drop_column("weather_snapshots", "precipitation")
    op.drop_column("wagers", "winnings")
    op.drop_column("wagers", "jackpot_multiplier")
    op.drop_column("wagers", "base_payout_multiplier")
    op.drop_column("wagers", "bucket_high")
    op.drop_column("wagers", "bucket_low")
    op.drop_column("wagers", "target")
    op.drop_column("wagers", "forecast_date")
