from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from src.core.config import config
from src.core.logger import logger


def get_default_timezone() -> str:
    app_env = config.APP_ENV.lower()
    logger.info(f"App environment: {app_env}")
    
    if app_env in ['staging', 'production', 'prod']:
        logger.info(f"Using production timezone for {app_env}: {config.DEFAULT_TIMEZONE_PRODUCTION}")
        return config.DEFAULT_TIMEZONE_PRODUCTION
    else:
        logger.info(f"Using development timezone for {app_env}: {config.DEFAULT_TIMEZONE_DEVELOPMENT}")
        return config.DEFAULT_TIMEZONE_DEVELOPMENT


def get_timezone_for_job(job) -> str:

    if job and hasattr(job, 'timezone_name') and job.timezone_name:
        return job.timezone_name
    
    return get_default_timezone()


def _get_timezone_object(timezone_str: str) -> ZoneInfo:
   
    try:
        return ZoneInfo(timezone_str)
    except Exception as e:
        logger.warning(f"Invalid timezone '{timezone_str}', falling back to default: {e}")
        default_tz = get_default_timezone()
        return ZoneInfo(default_tz)


def utc_to_timezone(utc_datetime: Optional[datetime], timezone_str: Optional[str] = None) -> Optional[datetime]:
    if utc_datetime is None:
        return None
    
    try:
        if timezone_str is None:
            timezone_str = get_default_timezone()
        
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_datetime.replace(tzinfo=ZoneInfo("UTC"))
        
        target_tz = _get_timezone_object(timezone_str)
        return utc_datetime.astimezone(target_tz)
    except Exception as e:
        logger.error(f"Error converting UTC to timezone '{timezone_str}': {e}")
        return utc_datetime


def timezone_to_utc(local_datetime: Optional[datetime], timezone_str: Optional[str] = None) -> Optional[datetime]:
    if local_datetime is None:
        return None
    
    try:
        if timezone_str is None:
            timezone_str = get_default_timezone()
        
        source_tz = _get_timezone_object(timezone_str)
        
        if local_datetime.tzinfo is None:
            local_datetime = local_datetime.replace(tzinfo=source_tz)
        
        utc_datetime = local_datetime.astimezone(ZoneInfo("UTC"))
        return utc_datetime.replace(tzinfo=None)
    except Exception as e:
        logger.error(f"Error converting local time to UTC: {e}")
        return local_datetime


def format_for_api(utc_datetime: Optional[datetime], timezone_str: Optional[str] = None) -> Optional[str]:

    if utc_datetime is None:
        return None
    
    try:
        local_dt = utc_to_timezone(utc_datetime, timezone_str)
        if local_dt:
            return local_dt.isoformat()
        return None
    except Exception as e:
        logger.error(f"Error formatting datetime for API: {e}")
        return utc_datetime.isoformat() if utc_datetime else None


def format_for_display(
    utc_datetime: Optional[datetime], 
    timezone_str: Optional[str] = None,
    format_string: str = "%Y-%m-%d %H:%M:%S %Z"
) -> Optional[str]:
    
    if utc_datetime is None:
        return None
    
    try:
        local_dt = utc_to_timezone(utc_datetime, timezone_str)
        if local_dt:
            return local_dt.strftime(format_string)
        return None
    except Exception as e:
        logger.error(f"Error formatting datetime for display: {e}")
        return str(utc_datetime) if utc_datetime else None


def get_timezone_abbreviation(timezone_str: Optional[str] = None) -> str:
    try:
        if timezone_str is None:
            timezone_str = get_default_timezone()
        
        tz = _get_timezone_object(timezone_str)
        now = datetime.now(tz)
        return now.strftime('%Z')
    except Exception as e:
        logger.error(f"Error getting timezone abbreviation: {e}")
        return "UTC"

