from typing import List, Union
from fastapi import APIRouter, Depends, File, Form, UploadFile, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.witnesses import apis
from src.witnesses.schema import (
    CreateWitnessFrontSchema,
    WitnessCreateSchema,
    WitnessNameUpdateSchema,
    WitnessSaveAllPayloadSchema,
)

witnesses_api = APIRouter(prefix="/witnesses", tags=["witnesses"])


@witnesses_api.get("/list/{job_no}", status_code=200)
async def get_witnesses_list_by_job(
    job_no: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await apis.get_witnesses_list_by_job(job_no, db)


@witnesses_api.get("/{job_no}/download_witnesses_complete_video", status_code=200, response_model=None)
async def download_witnesses_complete_video(
    job_no: int,
    witness_id: int,
    download_all: bool = Query(False, description="If true, merge and download all videos"),
    db: Session = Depends(get_db),
) -> Union[JSONResponse, FileResponse]:
    return await apis.download_witnesses_complete_video(job_no, witness_id, download_all, db)


@witnesses_api.post("/create-name", response_model=WitnessCreateSchema, status_code=201)
async def create_witness_name(
    data: CreateWitnessFrontSchema,
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await apis.create_witness_name(data, db)


@witnesses_api.patch("/name/{witness_id}", status_code=200)
async def update_witness_name(
    witness_id: int,
    payload: WitnessNameUpdateSchema,
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await apis.update_witness_name(witness_id, payload, db)


@witnesses_api.post("/save-all", status_code=200)
async def save_witness_and_videos(
    payload: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await apis.save_witness_and_videos(payload, files, db)


@witnesses_api.delete("/delete/{witness_id}", status_code=200)
async def delete_witness_by_id(
    witness_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await apis.delete_witness_by_id(witness_id, db)

