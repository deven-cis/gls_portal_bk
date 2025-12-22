from typing import List

from fastapi import Depends

from src.auth.utils import get_current_user
from src.cases.models import Cases
from src.users.models import Users
from src.core.logger import logger
from src.core.context import get_context
from fastapi import HTTPException, status
from src.cases.schema import CaseEditSchema, CaseSchema, GetCaseSchema, MarkCaseAsDoneSchema
from src.core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

cases_router = APIRouter(prefix="/case", tags=["case"])

@cases_router.get("/list", status_code=200)
async def list_cases(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    result = db.query(Cases).filter(Cases.is_archived == False).all()
    return JSONResponse(
        content={
            "status_code": status.HTTP_200_OK,
            "message": f"Found {len(result)} case(s)",
            "success": True,
            "result": [CaseSchema.model_validate(case).model_dump(mode="json") for case in result]
        },
        status_code=status.HTTP_200_OK
    )

@cases_router.get("/get/{case_id}", status_code=200)
async def get_case(case_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> JSONResponse:
    try:
        logger.info(f"Retrieving case {case_id}")
        case = db.query(Cases).filter(Cases.id == case_id, Cases.is_archived == False).first()
        if not case:
            logger.warning(f"Case {case_id} not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Case {case_id} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        logger.info(f"Case {case_id} fetched successfully")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Case {case_id} fetched successfully",
                "success": True,
                "result": GetCaseSchema.model_validate(case).model_dump()
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error getting case {case_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get case: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@cases_router.put("/edit/{case_id}", status_code=200)
async def edit_case(
    case_id: int, 
    case_data: CaseEditSchema, 
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    try:
        case = db.query(Cases).filter(Cases.id == case_id, Cases.is_archived == False).first()
        if not case:
            logger.warning(f'Case {case_id} not found')
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Case not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get ONLY the fields user actually sent (exclude unset and None values)
        update_data = case_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "No changes provided",
                    "success": True,
                    "result": GetCaseSchema.model_validate(case).model_dump()
                },
                status_code=status.HTTP_200_OK
            )
        
        # Update only the provided fields
        for field, value in update_data.items():
            if field == 'case_short_name' and isinstance(value, str):
                value = value.strip()
            setattr(case, field, value)
        
        case.save()
        logger.info(f'Case {case_id} updated successfully')

        # Return the updated values in the format expected by frontend
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Case updated successfully",
                "success": True,
                "result": GetCaseSchema.model_validate(case).model_dump()
            },
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error updating case {case_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update case: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    


@cases_router.patch("/mark_case_as_done/{case_no}", status_code=200)
async def mark_case_as_done(
    case_no: int,
    payload: MarkCaseAsDoneSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Mark a case as done or not done.
    Updates the mark_is_done field for the specified case.
    """
    try:
        logger.info(f"Marking case {case_no} as done: {payload.mark_is_done}")
        user_entered_by = get_context('entered_by')
        
        # Optimized single query with all filters
        case = (
            db.query(Cases)
            .filter(
                Cases.case_no == case_no,
                Cases.is_archived == False,
                Cases.entered_by == user_entered_by
            )
            .first()
        )
        
        if not case:
            logger.warning(f'Case {case_no} not found for user {user_entered_by}')
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Case not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Update mark_is_done status
        mark_is_done = payload.mark_is_done
        case.mark_is_done = mark_is_done
        db.commit()
        db.refresh(case)
        
        logger.info(f'Case {case_no} marked as done: {mark_is_done}')
        
        # Simplified response message
        message = "Case marked as done successfully" if mark_is_done else "Case marked as not done successfully"
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": {
                    "case_no": case.case_no,
                    "mark_is_done": case.mark_is_done
                }
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking case {case_no} as done: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to mark case as done",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )