from typing import List, Optional
from fastapi import APIRouter, Query, Form, File, UploadFile, Depends
from fastapi.responses import FileResponse
from src.auth.utils import get_current_user

from src.witnesses.apis import (
    list_witnesses, get_witness, create_witness, update_witness, delete_witness,
    add_witness_video, list_witness_videos, download_witness_video, delete_witness_video, get_job_witnesses, create_witness_name
)
from src.witnesses.schema import WitnessSchema, WitnessVideoSchema, GetJobWitnessSchema, WitnessNameSchema, CreateWitnessFrontSchema, WitnessUpdateResponseSchema, WitnessUpdateSchema
from src.witnesses.utils import get_witness_update_data_from_request
from src.core.database import get_db
from sqlalchemy.orm import Session

witnesses_router = APIRouter(prefix='/witnesses', tags=['witnesses'])


@witnesses_router.get('', response_model=List[WitnessSchema])
async def list_witnesses_route(
    job_no: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await list_witnesses(job_no=job_no, current_user=current_user, db=db)


@witnesses_router.get('/get/{job_no}', response_model=List[GetJobWitnessSchema])
async def get_job_witnesses_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await get_job_witnesses(job_no=job_no, current_user=current_user, db=db)


@witnesses_router.get('/{witness_id}', response_model=WitnessSchema)
async def get_witness_route(witness_id: int, db = Depends(get_db)):
    return await get_witness(witness_id, db=db)


@witnesses_router.post('/create-name', response_model=WitnessNameSchema, status_code=201)
async def create_witness_name_route(
    payload: CreateWitnessFrontSchema,
    db: Session = Depends(get_db)
):
    return await create_witness_name(
        data=payload,
        db=db
    )


@witnesses_router.post('', response_model=WitnessSchema, status_code=201)
async def create_witness_route(
    job_no: int = Form(...),
    witness_name: str = Form(...),
    witness_email: Optional[str] = Form(None),
    read_on_text: str = Form(...),
    read_on_time: str = Form(...),
    read_off_text: str = Form(...),
    read_off_time: str = Form(...),
    db: Session = Depends(get_db)
):
    return await create_witness(
        job_no=job_no,
        witness_name=witness_name,
        witness_email=witness_email,
        read_on_text=read_on_text,
        read_on_time=read_on_time,
        read_off_text=read_off_text,
        read_off_time=read_off_time,
        db=db
    )


@witnesses_router.put('/{witness_id}', response_model=WitnessUpdateResponseSchema, status_code=200)
async def update_witness_route(
    witness_id: int,
    update_data: WitnessUpdateSchema = Depends(get_witness_update_data_from_request),
    db: Session = Depends(get_db)
):
    """
    Update witness. Form field types are defined in WitnessUpdateSchema to avoid repetition.
    """
    return await update_witness(
        witness_id=witness_id,
        update_data=update_data,
        db=db
    )


@witnesses_router.delete('/{witness_id}', status_code=204)
async def delete_witness_route(witness_id: int, db: Session = Depends(get_db)):
    return await delete_witness(witness_id, db=db)


@witnesses_router.post('/{witness_id}/videos', response_model=WitnessVideoSchema, status_code=201)
async def add_witness_video_route(
    witness_id: int,
    job_no: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    video: UploadFile = File(...),
    chunk_number: Optional[int] = Form(None),
    upload_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    return await add_witness_video(
        witness_id=witness_id,
        job_no=job_no,
        start_time=start_time,
        end_time=end_time,
        video=video,
        chunk_number=chunk_number,
        upload_id=upload_id,
        db=db
    )


@witnesses_router.get('/videos/list', response_model=List[WitnessVideoSchema])
async def list_witness_videos_route(
    witness_id: Optional[int] = Query(None),
    job_no: Optional[int] = Query(None),
    db   = Depends(get_db)
):
    return await list_witness_videos(witness_id=witness_id, job_no=job_no, db=db)


@witnesses_router.get('/videos/{video_id}/download')
async def download_witness_video_route(video_id: int, db: Session = Depends(get_db)):
    return await download_witness_video(video_id, db=db)


@witnesses_router.delete('/videos/{video_id}', status_code=204)
async def delete_witness_video_route(video_id: int, db: Session = Depends(get_db)):
    return await delete_witness_video(video_id, db=db)
