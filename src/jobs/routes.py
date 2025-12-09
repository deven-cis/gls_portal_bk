from typing import List
from fastapi import APIRouter

from src.jobs.apis import list_jobs, list_pending_jobs, list_upcoming_jobs, list_jobs_by_case
from src.jobs.schema import JobSchema


jobs_router = APIRouter(prefix='/jobs', tags=['jobs'])

jobs_router.add_api_route(
    '',
    list_jobs,
    methods=['GET'],
    response_model=List[JobSchema],
)

jobs_router.add_api_route(
    '/list_of_cases_jobs/',
    list_jobs_by_case,
    methods=['GET'],
    response_model=List[JobSchema],
)

jobs_router.add_api_route(
    '/pending/',
    list_pending_jobs   ,
    methods=['GET'],
    response_model=List[JobSchema],
)   
 
jobs_router.add_api_route(
    '/upcoming/',
    list_upcoming_jobs,
    methods=['GET'],
    response_model=List[JobSchema],
)

# jobs_router.add_api_route(
#     '/{job_id}/cancel',
#     cancel_job,
#     methods=['POST'],
#     response_model=JobSchema,
# )
