from typing import List

from fastapi import Depends

from src.auth.utils import get_current_user
from src.cases.models import Cases
from src.users.models import Users
from src.core.logger import logger
from src.core.context import get_context
from fastapi import HTTPException, status
from src.cases.schema import CaseEditSchema

async def list_cases(
    current_user: dict = Depends(get_current_user),
) -> List[Cases]:
    
    logger.info(f'Listing cases for user: {current_user.get("id")}')
    user_info = get_context('entered_by')
    result = Cases.fetch_records({"entered_by": user_info})
    return result


async def edit_case(
    case_id: int,
    case_data: CaseEditSchema,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update case_short_name and case_number for a specific case"""
    case = Cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail='Case not found')
    
    if case.entered_by != get_context('entered_by'):
        raise HTTPException(status_code=403, detail='Not authorized')
    
    # Update allowed fields
    if case_data.case_short_name is not None:
        case.case_short_name = case_data.case_short_name
    if case_data.case_number is not None:
        case.case_number = case_data.case_number
    
    case.save()
    return {
        'id': case.id,
        'case_short_name': case.case_short_name,
        'case_number': case.case_number,
        'message': 'Case updated'
    }

    