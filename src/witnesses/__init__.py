from typing import List, Union
from fastapi import APIRouter, Depends, File, Form, UploadFile, Query, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.witnesses.apis import (
    get_witnesses_list_by_job,
    download_witnesses_complete_video,
    create_witness_name,
    update_witness_name,
    init_witness_video_upload,
    upload_witness_video_chunk,
    complete_witness_video_upload,
    pause_witness_video_upload,
    resume_witness_video_upload,
    cancel_witness_video_upload,
    trigger_uploaded_video_cleanup,
    save_witness_and_videos,
    delete_witness_by_id,
    get_witness_video_download_link
)
from src.witnesses.schema import (
    CreateWitnessFrontSchema,
    WitnessCreateSchema,
    WitnessNameUpdateSchema,
    WitnessVideoUploadInitSchema,
    WitnessVideoUploadCompleteSchema,
    WitnessVideoUploadPauseSchema,
    WitnessVideoUploadResumeSchema,
    WitnessVideoUploadCancelSchema,
)

witnesses_api = APIRouter(prefix="/witnesses", tags=["witnesses"])


@witnesses_api.get("/list/{job_no}", status_code=200)
async def get_witnesses_list_by_job_endpoint(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await get_witnesses_list_by_job(job_no, db)


@witnesses_api.get("/videos/{video_id}/download-link", status_code=200)
async def get_witness_video_download_link_endpoint(
    video_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")
    return await get_witness_video_download_link(video_id, db, request_base_url=base_url)


@witnesses_api.get("/{job_no}/download_witnesses_complete_video", status_code=200, response_model=None)
async def download_witnesses_complete_video_endpoint(
    job_no: int,
    witness_id: int,
    download_all: bool = Query(False, description="If true, merge and download all videos"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[JSONResponse, FileResponse]:
    return await download_witnesses_complete_video(job_no, witness_id, download_all, db)


@witnesses_api.post("/create-name", response_model=WitnessCreateSchema, status_code=201)
async def create_witness_name_endpoint(
    data: CreateWitnessFrontSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await create_witness_name(data, db)


@witnesses_api.patch("/name/{witness_id}", status_code=200)
async def update_witness_name_endpoint(
    witness_id: int,
    payload: WitnessNameUpdateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await update_witness_name(witness_id, payload, db)


@witnesses_api.post("/uploads/init", status_code=201)
async def init_witness_video_upload_endpoint(
    data: WitnessVideoUploadInitSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await init_witness_video_upload(data, db)


@witnesses_api.post("/uploads/chunk", status_code=200)
async def upload_witness_video_chunk_endpoint(
    upload_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await upload_witness_video_chunk(upload_id, chunk_number, total_chunks, file, db)


@witnesses_api.post("/uploads/complete", status_code=200)
async def complete_witness_video_upload_endpoint(
    data: WitnessVideoUploadCompleteSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await complete_witness_video_upload(data, db)

@witnesses_api.post("/uploads/pause", status_code=200)
async def pause_witness_video_upload_endpoint(
    data: WitnessVideoUploadPauseSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await pause_witness_video_upload(data, db)


@witnesses_api.post("/uploads/resume", status_code=200)
async def resume_witness_video_upload_endpoint(
    data: WitnessVideoUploadResumeSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await resume_witness_video_upload(data, db)


@witnesses_api.post("/uploads/cancel", status_code=200)
async def cancel_witness_video_upload_endpoint(
    data: WitnessVideoUploadCancelSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await cancel_witness_video_upload(data, db)


@witnesses_api.post("/uploads/debug/cleanup-expired", status_code=200)
async def trigger_uploaded_video_cleanup_endpoint(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await trigger_uploaded_video_cleanup(db)


@witnesses_api.post("/save-all", status_code=200)
async def save_witness_and_videos_endpoint(
    payload: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await save_witness_and_videos(payload, files, db)


@witnesses_api.delete("/delete/{witness_id}", status_code=200)
async def delete_witness_by_id_endpoint(
    witness_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await delete_witness_by_id(witness_id, db)
