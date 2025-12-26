"""Initial schema: users, wagers, weather_snapshots.

Revision ID: 001
Revises:
Create Date: 2025-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("credits_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "wagers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("odds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_wagers_user_id", "wagers", ["user_id"], unique=False)
    op.create_index("ix_wagers_status", "wagers", ["status"], unique=False)

    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_weather_snapshots_date", "weather_snapshots", ["date"], unique=False)
    op.create_index("ix_weather_snapshots_location", "weather_snapshots", ["location"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_weather_snapshots_location", "weather_snapshots")
    op.drop_index("ix_weather_snapshots_date", "weather_snapshots")
    op.drop_table("weather_snapshots")
    op.drop_index("ix_wagers_status", "wagers")
    op.drop_index("ix_wagers_user_id", "wagers")
    op.drop_table("wagers")
    op.drop_index("ix_users_username", "users")
    op.drop_table("users")
