"""APScheduler: daily ingestion, resolution, reset."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.odds_service import db, ingestion_service
from backend import resolution
from backend import reset_service
from backend import lifecycle_service

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _run_ingestion():
    try:
        with db.get_db_connection() as conn:
            # Calls the existing run_full_ingestion in odds_service which handles both actuals and forecasts
            results = ingestion_service.run_full_ingestion(conn)
        logger.info(f"Scheduled ingestion completed: {results}")
    except Exception as e:
        logger.exception("Scheduled ingestion failed: %s", e)


def _run_resolution():
    try:
        resolution.resolve_wagers()
        logger.info("Scheduled wager resolution completed")
    except Exception as e:
        logger.exception("Scheduled resolution failed: %s", e)


def _run_reset():
    try:
        reset_service.reset_daily()
    except Exception as e:
        logger.exception("Scheduled reset failed: %s", e)


def _run_purge():
    try:
        # Default retention is 365 days (1 year) as approved
        lifecycle_service.purge_old_data(retention_days=365)
    except Exception as e:
        logger.exception("Scheduled data purge failed: %s", e)


def start_scheduler():
    """Schedule daily jobs: 4:00 purge, 6:00 ingestion, 6:15 resolution, 0:00 reset (America/Chicago)."""
    scheduler.add_job(
        _run_purge,
        CronTrigger(hour=4, minute=0, timezone="America/Chicago"),
        id="purge_data",
    )
    scheduler.add_job(
        _run_ingestion,
        CronTrigger(hour=6, minute=0, timezone="America/Chicago"),
        id="ingestion",
    )
    scheduler.add_job(
        _run_resolution,
        CronTrigger(hour=6, minute=15, timezone="America/Chicago"),
        id="resolution",
    )
    scheduler.add_job(
        _run_reset,
        CronTrigger(hour=0, minute=0, timezone="America/Chicago"),
        id="reset",
    )
    scheduler.start()
    logger.info("APScheduler started (purge 4:00, ingestion 6:00, resolution 6:15, reset 0:00 CT)")


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
