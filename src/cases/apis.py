from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.cases.models import Cases
from src.cases.schema import CaseEditSchema, CaseSchema, GetCaseSchema
from src.core.logger import logger
from src.core.timezone_utils import get_timezone_now
from src.core.context import get_context


async def list_cases(db: Session) -> JSONResponse:
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


async def get_case(case_id: int, db: Session) -> JSONResponse:

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


async def edit_case(case_id: int, case_data: CaseEditSchema, db: Session) -> JSONResponse:
    
    try:
        entered_by = get_context("entered_by")
        now = get_timezone_now()
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

        update_data = case_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            logger.warning(f'No changes provided for case {case_id}')
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "No changes provided",
                    "success": True,
                    "result": GetCaseSchema.model_validate(case).model_dump()
                },
                status_code=status.HTTP_200_OK
            )
        
        for field, value in update_data.items():
            if field == 'case_short_name' and isinstance(value, str):
                value = value.strip()
            setattr(case, field, value)
        
        case.last_modified_at = now
        case.last_modified_by = entered_by
        db.add(case)
        db.commit()
        logger.info(f'Case {case_id} updated successfully')

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
        db.rollback()
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update case: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
