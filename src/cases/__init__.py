from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.cases import apis
from src.cases.schema import CaseSchema, CaseEditSchema, GetCaseSchema

cases_router = APIRouter(prefix='/case', tags=['case'])


@cases_router.get("/list", status_code=200, response_model=List[CaseSchema])
async def list_cases(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await apis.list_cases(db)


@cases_router.get("/get/{case_id}", status_code=200, response_model=GetCaseSchema)
async def get_case(
    case_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await apis.get_case(case_id, db)


@cases_router.put("/edit/{case_id}", status_code=200, response_model=CaseEditSchema)
async def edit_case(
    case_id: int,
    case_data: CaseEditSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await apis.edit_case(case_id, case_data, db)

