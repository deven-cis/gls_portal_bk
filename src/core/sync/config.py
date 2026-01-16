from datetime import date
from src.core.config import config
from src.core.logger import logger


def get_sync_date_range(days: int = None) -> tuple:
    if days is None:
        days = config.SYNC_DATA_DAYS
    
    end_date = date(2008, 7, 19)
    start_date = date(2008, 7, 19)
    
    logger.info(f"Sync date range: {start_date} to {end_date} ({days} days)")
    return start_date, end_date


def get_sync_batch_size() -> int:
    return 2


def get_sync_interval_minutes() -> int:
    return config.SYNC_INTERVAL_MINUTES

