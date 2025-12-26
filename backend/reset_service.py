"""Daily reset: port of Windfall DailyResetService (reset daily claims)."""

import logging
from backend.odds_service import db

logger = logging.getLogger(__name__)


def reset_daily():
    """
    Run daily reset logic.
    Windfall reset: customerRepository.resetAllDailyClaims() at midnight CST.
    CardinalCast: Daily claims are now date-based (User.last_daily_claim_date).
    We log this event; the logic is handled at claim-time.
    """
    logger.info("Daily reset run (rolling claims logic in place; no DB reset needed)")
