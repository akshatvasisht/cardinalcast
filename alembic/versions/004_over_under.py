"""Add Over/Under fields to Wager

Revision ID: 004_over_under
Revises: 003_daily_claims
Create Date: 2024-02-12 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = '004_over_under'
down_revision = '003_daily_claims'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('wagers', sa.Column('wager_kind', sa.String(), nullable=False, server_default="BUCKET"))
    op.add_column('wagers', sa.Column('direction', sa.String(), nullable=True))
    op.add_column('wagers', sa.Column('predicted_value', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('wagers', 'predicted_value')
    op.drop_column('wagers', 'direction')
    op.drop_column('wagers', 'wager_kind')
