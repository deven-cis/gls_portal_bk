from typing import List

from fastapi import Depends

from src.auth.utils import get_current_user
from src.cases.models import Cases
from src.users.models import Users
from src.core.logger import logger
from src.core.context import get_context

async def list_cases(
    current_user: dict = Depends(get_current_user),
) -> List[Cases]:
    
    logger.info(f'Listing cases for user: {current_user.get("id")}')
    user_info = get_context('entered_by')
    result = Cases.fetch_records({"entered_by": user_info})
    return result
