"""Daily reset: reset daily claims at midnight CST."""

import logging
from backend.odds_service import db

logger = logging.getLogger(__name__)


def reset_daily():
    """
    Run daily reset logic.
    Daily claims are date-based (User.last_daily_claim_date).
    We log this event; the logic is handled at claim-time.
    """
    logger.info("Daily reset run (rolling claims logic in place; no DB reset needed)")
