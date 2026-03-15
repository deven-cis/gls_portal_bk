"""
RBAC (Role-Based Access Control) utilities for the application.
Simple role-based authorization based on priority_level.
"""

from typing import Optional
from src.core.logger import logger
from src.core.context import get_context


def get_current_user_role() -> Optional[str]:
    """Get current user's priority_level (role)"""
    return get_context('rsrc_role') or get_context('priority_level')


def get_current_user_rsrc_no() -> Optional[int]:
    """Get current user's rsrc_no"""
    return get_context('rsrc_no')


def is_admin_role(priority_level: str) -> bool:
    """Check if priority_level indicates admin access (shows all records)"""
    if not priority_level:
        return False
    # Admin roles typically contain keywords like "admin", "manager", "supervisor"
    # or specific patterns that grant full access
    admin_keywords = ["1b. Staff: Videographers Georgia"]
    return any(keyword in priority_level.lower() for keyword in admin_keywords)
