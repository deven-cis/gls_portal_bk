from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from src.core.config import config
from src.core.logger import logger


def get_default_timezone() -> str:
    app_env = config.APP_ENV.lower()
    
    if app_env in ['staging', 'production']:
        return config.DEFAULT_TIMEZONE_PRODUCTION
    else:
        return config.DEFAULT_TIMEZONE_DEVELOPMENT


def _get_timezone_object(timezone_str: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_str)
    except Exception as e:
        logger.warning(f"Invalid timezone '{timezone_str}', using default: {e}")
        return ZoneInfo(get_default_timezone())


def convert_to_timezone(utc_datetime: Optional[datetime], timezone_str: Optional[str] = None) -> Optional[datetime]:
    if utc_datetime is None:
        return None
    
    try:
        timezone_str = timezone_str or get_default_timezone()
        target_tz = _get_timezone_object(timezone_str)
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_datetime.replace(tzinfo=ZoneInfo("UTC"))
        
        return utc_datetime.astimezone(target_tz)
    except Exception as e:
        logger.error(f"Error converting to timezone: {e}")
        return utc_datetime


def get_timezone_now() -> datetime:
    try:
        utc_now = datetime.now(ZoneInfo("UTC"))
        local_time = convert_to_timezone(utc_now)
        
        if local_time and local_time.tzinfo:
            return local_time.replace(tzinfo=None)
        
        return local_time or utc_now
    except Exception as e:
        logger.error(f"Error getting timezone now: {e}")
        return datetime.now(ZoneInfo("UTC"))


def get_est_now() -> datetime:
    try:
        est_tz = ZoneInfo("America/New_York")
        est_now = datetime.now(est_tz)
        return est_now.replace(tzinfo=None)
    except Exception as e:
        logger.error(f"Error getting EST time: {e}")
        return datetime.utcnow()
