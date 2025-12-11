from typing import List

from fastapi import APIRouter

from src.cases.apis import list_cases, edit_case, get_case
from src.cases.schema import CaseSchema, CaseEditSchema, GetCaseSchema


cases_router = APIRouter(prefix='/case', tags=['case'])


cases_router.add_api_route(
    '/list',
    list_cases,
    methods=['GET'],
    response_model=List[CaseSchema],
)

cases_router.add_api_route(
    '/edit/{case_id}',
    edit_case,
    methods=['PUT'],
    response_model=CaseEditSchema,
)

cases_router.add_api_route(
    '/get/{case_id}',
    get_case,
    methods=['GET'],
    response_model=GetCaseSchema,
)