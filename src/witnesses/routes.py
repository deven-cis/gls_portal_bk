from typing import List, Optional
from fastapi import APIRouter, Query, Form, File, UploadFile, Depends
from fastapi.responses import FileResponse
from src.auth.utils import get_current_user

from src.witnesses.apis import (
    list_witnesses, get_witness, create_witness, update_witness, delete_witness,
    add_witness_video, list_witness_videos, download_witness_video, delete_witness_video, get_job_witnessee
)
from src.witnesses.schema import WitnessSchema, WitnessVideoSchema, GetJobWitnessSchema


witnesses_router = APIRouter(prefix='/witnesses', tags=['witnesses'])


@witnesses_router.get('', response_model=List[WitnessSchema])
async def list_witnesses_route(job_no: Optional[int] = Query(None)):
    return await list_witnesses(job_no=job_no)


@witnesses_router.get('/get/{job_no}', response_model=List[GetJobWitnessSchema])
async def get_job_witnesses_route(
    job_no: int,
    current_user: dict = Depends(get_current_user)
):
    return await get_job_witnessee(job_no=job_no, current_user=current_user)


@witnesses_router.get('/{witness_id}', response_model=WitnessSchema)
async def get_witness_route(witness_id: int):
    return await get_witness(witness_id)


@witnesses_router.post('', response_model=WitnessSchema, status_code=201)
async def create_witness_route(
    job_no: int = Form(...),
    witness_name: str = Form(...),
    witness_email: Optional[str] = Form(None),
    read_on_text: str = Form(...),
    read_on_time: str = Form(...),
    read_off_text: str = Form(...),
    read_off_time: str = Form(...),
):
    return await create_witness(
        job_no=job_no,
        witness_name=witness_name,
        witness_email=witness_email,
        read_on_text=read_on_text,
        read_on_time=read_on_time,
        read_off_text=read_off_text,
        read_off_time=read_off_time,
    )


@witnesses_router.put('/{witness_id}', response_model=WitnessSchema)
async def update_witness_route(
    witness_id: int,
    witness_name: Optional[str] = Form(None),
    witness_email: Optional[str] = Form(None),
    actual_start_time: Optional[str] = Form(None),
    actual_end_time: Optional[str] = Form(None),
    read_sign_date: Optional[str] = Form(None),
    read_sign_to: Optional[int] = Form(None),
    read_on_text: Optional[str] = Form(None),
    read_on_time: Optional[str] = Form(None),
    read_off_text: Optional[str] = Form(None),
    read_off_time: Optional[str] = Form(None),
):
    return await update_witness(
        witness_id=witness_id,
        witness_name=witness_name,
        witness_email=witness_email,
        actual_start_time=actual_start_time,
        actual_end_time=actual_end_time,
        read_sign_date=read_sign_date,
        read_sign_to=read_sign_to,
        read_on_text=read_on_text,
        read_on_time=read_on_time,
        read_off_text=read_off_text,
        read_off_time=read_off_time,
    )


@witnesses_router.delete('/{witness_id}', status_code=204)
async def delete_witness_route(witness_id: int):
    return await delete_witness(witness_id)


@witnesses_router.post('/{witness_id}/videos', response_model=WitnessVideoSchema, status_code=201)
async def add_witness_video_route(
    witness_id: int,
    job_no: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    video: UploadFile = File(...),
    chunk_number: Optional[int] = Form(None),
    upload_id: Optional[str] = Form(None),
):
    return await add_witness_video(
        witness_id=witness_id,
        job_no=job_no,
        start_time=start_time,
        end_time=end_time,
        video=video,
        chunk_number=chunk_number,
        upload_id=upload_id,
    )


@witnesses_router.get('/videos/list', response_model=List[WitnessVideoSchema])
async def list_witness_videos_route(
    witness_id: Optional[int] = Query(None),
    job_no: Optional[int] = Query(None),
):
    return await list_witness_videos(witness_id=witness_id, job_no=job_no)


@witnesses_router.get('/videos/{video_id}/download')
async def download_witness_video_route(video_id: int):
    return await download_witness_video(video_id)


@witnesses_router.delete('/videos/{video_id}', status_code=204)
async def delete_witness_video_route(video_id: int):
    return await delete_witness_video(video_id)

