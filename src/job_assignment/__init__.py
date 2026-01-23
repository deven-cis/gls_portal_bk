from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.job_assignment.apis import reassign_job_service
from src.job_assignment.schema import JobReassignRequestSchema

job_assignment_apis = APIRouter(prefix='/jobs', tags=['jobs'])


@job_assignment_apis.post("/reassign", status_code=200)
async def reassign_job_route_endpoint(
    payload: JobReassignRequestSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await reassign_job_service(payload, db)

