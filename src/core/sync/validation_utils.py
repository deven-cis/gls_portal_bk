"""
Validation utilities for sync services.
"""

import re
from typing import Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session

from src.core.logger import logger


def validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> Tuple[bool, Optional[str]]:
    if start_date is None or end_date is None:
        return True, None  
    
    if start_date > end_date:
        error_msg = f"Invalid date range: start_date ({start_date}) is after end_date ({end_date})"
        logger.warning(f"[VALIDATION] {error_msg}")
        return False, error_msg
    
    return True, None


def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
    if not email or not isinstance(email, str):
        return False, "Email is empty or not a string"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email.strip()):
        error_msg = f"Invalid email format: {email}"
        logger.warning(f"[VALIDATION] {error_msg}")
        return False, error_msg
    
    return True, None


def normalize_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    
    return str(value).strip() if str(value).strip() else None


def validate_string_length(value: str, max_length: int, field_name: str) -> Tuple[bool, Optional[str]]:
    if value is None:
        return True, None  
    
    if not isinstance(value, str):
        return False, f"{field_name} must be a string"
    
    if len(value) > max_length:
        error_msg = f"{field_name} exceeds maximum length of {max_length} characters (got {len(value)})"
        logger.warning(f"[VALIDATION] {error_msg}")
        return False, error_msg
    
    return True, None


def check_email_uniqueness(db: Session, email: str, exclude_rsrc_no: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    if not email:
        return False, "Email is required"
    
    try:
        from src.resources.models import Resources

        query = db.query(Resources).filter(Resources.email == email.strip().lower())

        if exclude_rsrc_no is not None:
            query = query.filter(Resources.rsrc_no != exclude_rsrc_no)

        existing_resource = query.first()

        if existing_resource:
            error_msg = f"Email '{email}' already exists (rsrc_no={existing_resource.rsrc_no})"
            logger.warning(f"[VALIDATION] {error_msg}")
            return False, error_msg
        
        return True, None
    
    except Exception as e:
        logger.error(f"[VALIDATION] Error checking email uniqueness: {str(e)}", exc_info=True)
        return True, None


