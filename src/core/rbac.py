from typing import Optional
from src.core.logger import logger
from src.core.context import get_context
ADMIN_ROLES = [
    "1b. Staff: Videographers Georgia",
]

def get_current_user_role() -> Optional[str]:
    return get_context('rsrc_role') or get_context('priority_level')


def get_current_user_rsrc_no() -> Optional[int]:
    return get_context('rsrc_no')


def is_admin_role(priority_level: str) -> bool:
    if not priority_level:
        return False
    return priority_level.strip() in ADMIN_ROLES
