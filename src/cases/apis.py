from typing import List

from fastapi import Depends

from src.auth.utils import get_current_user
from src.cases.models import Cases
from src.users.models import Users
from src.core.logger import logger
from src.core.context import get_context
from fastapi import HTTPException, status
from src.cases.schema import CaseEditSchema
from src.core.database import get_db

async def list_cases(
    current_user: dict = Depends(get_current_user),
) -> List[Cases]:
    
    logger.info(f'Listing cases for user: {current_user.get("entered_by")}')
    user_info = get_context('entered_by')
    logger.info(f'User info: {user_info}')
    result = Cases.fetch_records({"entered_by": user_info})
    return result

async def get_case(case_id: int, current_user: dict = Depends(get_current_user), db= Depends(get_db)) -> Cases:
    logger.info(f"Retrieving case {case_id}")
    case = db.query(Cases).filter(Cases.id == case_id, Cases.is_archived == False).first()
    logger.info(f"Case {case} fetched successfully")
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def edit_case(
    case_id: int, 
    case_data: CaseEditSchema, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
    ) -> dict:
    try:
        case = Cases.get(case_id)
        if not case or case.is_archived:
            logger.warning(f'Case {case_id} not found')
            raise HTTPException(404, "Case not found")

        # Get ONLY the fields user actually sent (exclude unset and None values)
        update_data = case_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return {
                "id": case.id,
                "case_short_name": case.case_short_name,
                "case_number": case.case_number,
                "message": "No changes provided"
            }
        
        # Update only the provided fields
        for field, value in update_data.items():
            # Skip empty strings for important fields
            if field in ['case_short_name'] and isinstance(value, str) and not value.strip():
                continue
            setattr(case, field, value)
        
        case.save()
        logger.info(f'Case {case_id} updated successfully')

        return {
            "id": case.id,
            "case_short_name": case.case_short_name,
            "case_number": case.case_number,
            "message": "Case updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case {case_id}: {str(e)}", exc_info=True)
        raise HTTPException(500, "Failed to update case")

    
