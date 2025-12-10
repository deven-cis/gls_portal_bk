from typing import List

from fastapi import APIRouter

from src.cases.apis import list_cases, edit_case
from src.cases.schema import CaseSchema, CaseEditSchema


cases_router = APIRouter(prefix='/cases', tags=['cases'])


cases_router.add_api_route(
    '',
    list_cases,
    methods=['GET'],
    response_model=List[CaseSchema],
)

cases_router.add_api_route(
    '/{case_id}',
    edit_case,
    methods=['PUT'],
    response_model=CaseEditSchema,
)