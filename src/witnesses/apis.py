from typing import List, Optional, Union
import json
from datetime import datetime, time as dt_time
from pathlib import Path
from fastapi import status, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session, joinedload, with_loader_criteria
from src.core.context import get_context
from src.core.logger import logger
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.core.file_utils import save_video_file
from src.witnesses.schema import (
    CreateWitnessFrontSchema,
    WitnessCreateSchema,
    WitnessNameUpdateSchema,
    WitnessSaveAllPayloadSchema,
    WitnessSchema,
)


def _normalize_time_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    if value.count(":") == 1:
        value = f"{value}:00"
    try:
        t = dt_time.fromisoformat(value)
        return str(t)
    except Exception:
        return None


async def get_witnesses_list_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        witnesses: List[Witnesses] = (
            db.query(Witnesses)
            .options(
                joinedload(Witnesses.witness_vid),
                with_loader_criteria(
                    WitnessVideos, WitnessVideos.is_archived == False, include_aliases=True
                ),
            )
            .filter(Witnesses.job_no == job_no, ~Witnesses.is_archived)
            .all()
        )

        data = [WitnessSchema.model_validate(w).model_dump(mode="json") for w in witnesses]
        logger.info(f"Witnesses data witnesses list for job_no {job_no}: {len(data)}")
        return data
    except Exception as e:
        logger.error(
            f"Error getting witnesses list for job_no {job_no}: {str(e)}", exc_info=True
        )
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get witnesses: {str(e)}",
                "success": False,
                "result": [],
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def download_witnesses_complete_video(
    job_no: int,
    witness_id: int,
    download_all: bool,
    db: Session,
) -> Union[JSONResponse, FileResponse]:
    try:
        from src.jobs.apis import get_witnesses_with_videos
        from src.jobs.apis import merge_videos_ffmpeg
        
        witnesses = get_witnesses_with_videos(job_no, db, witness_id=witness_id)
        if download_all:
            logger.info(f"Downloading witnesses complete video for job_no {job_no}")
            video_paths = []
            for witness in witnesses:
                for video in witness.witness_vid:
                    if video.file_path and Path(video.file_path).exists():
                        video_paths.append(video.file_path)
                
                merged_file_path = merge_videos_ffmpeg(video_paths, job_no)
                merged_filename = merged_file_path.name
                
                return FileResponse(
                    path=str(merged_file_path),
                    filename=merged_filename,
                    media_type='video/mp4',
                    headers={
                        "Content-Disposition": f"attachment; filename={merged_filename}"
                    }
                )
        else:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "download_all is required",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    except Exception as e:
        logger.error(f"Error downloading witnesses complete video: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to download witnesses complete video: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def create_witness_name(data: CreateWitnessFrontSchema, db: Session) -> JSONResponse:
    try:
        import importlib
        jobs_models = importlib.import_module('src.jobs.models')
        cases_models = importlib.import_module('src.cases.models')
        Jobs = jobs_models.Jobs
        Cases = cases_models.Cases
        
        job = db.query(Jobs).filter(Jobs.job_no == data.job_no).first()
        if not job:
            logger.error(f"Job with job_no {data.job_no} not found")
            return JSONResponse(
                content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": f"Failed to create witness: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        case_info = db.query(Cases).filter(Cases.case_no == job.case_no).first()

        read_context = {
            "read_on_text": (
                f"We are now on the record at [Time] on [Date]. This is the [Type] deposition of "
                f"{data.witness_name} in the matter of {case_info.case_short_name} case number {case_info.case_number}"
            ),
            "read_off_text": (
                f"We are now off the record at [Time]. This concludes the deposition of {data.witness_name}"
            ),
        }

        witness = Witnesses(
            job_no=data.job_no,
            witness_name=data.witness_name,
            read_on_text=read_context["read_on_text"],
            read_off_text=read_context["read_off_text"],
        )
        witness.save()

        witness_data = WitnessCreateSchema.model_validate(witness).model_dump(mode="json")
        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Witness created successfully",
                "success": True,
                "result": witness_data,
            },
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        logger.error(f"Error creating witness: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to create witness: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def update_witness_name(
    witness_id: int,
    payload: WitnessNameUpdateSchema,
    db: Session,
) -> JSONResponse:
    entered_by = get_context("entered_by") or 0
    now = datetime.utcnow()

    try:
        name = (payload.witness_name or "").strip()
        if not name:
            logger.error(f"Witness name cannot be empty")
            return JSONResponse(
                content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Failed to update witness name: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        witness = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            ~Witnesses.is_archived,
        ).first()
        if not witness:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Witness with id {witness_id} not found",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        witness.witness_name = name
        witness.last_modified_at = now
        witness.last_modified_by = entered_by
        db.commit()
        db.refresh(witness)

        witness_data = WitnessSchema.model_validate(witness).model_dump(mode="json")
        logger.info(f"Witness name updated successfully for witness_id {witness_id}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Witness name updated successfully",
                "success": True,
                "result": witness_data,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating witness name {witness_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update witness name: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def save_witness_and_videos(
    payload: str,
    files: List[UploadFile],
    db: Session,
) -> JSONResponse:
    entered_by = get_context("entered_by") or 0
    now = datetime.utcnow()

    try:
        raw = json.loads(payload)
        data = WitnessSaveAllPayloadSchema.model_validate(raw)
    except Exception as e:
        logger.error(f"Invalid payload JSON: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": f"Invalid payload JSON: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        if not data.witness_id:
            logger.error(f"Witness ID is required for save/update")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "witness_id is required for save/update",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        witness: Optional[Witnesses] = db.query(Witnesses).filter(
            Witnesses.id == data.witness_id,
            ~Witnesses.is_archived,
        ).first()
        if not witness:
            logger.error(f"Witness with id {data.witness_id} not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Failed to save witness/videos: {str(e)}",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if witness.job_no != data.job_no:
            logger.error(f"job_no mismatch for witness {witness.id} (expected {witness.job_no}, got {data.job_no})")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": f"job_no mismatch for witness {witness.id} (expected {witness.job_no}, got {data.job_no})",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        logger.info(f"Witness updated successfully for witness_id {data.witness_id}")

        witness.last_modified_at = now
        witness.last_modified_by = entered_by

        if data.witness_name is not None:
            new_name = str(data.witness_name).strip()
            if not new_name:
                logger.error(f"Witness name cannot be empty")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "witness_name cannot be empty",
                        "success": False,
                        "result": {},
                    },
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            logger.info(f"Witness name updated successfully for witness_id {data.witness_id}")
            witness.witness_name = new_name

        if data.witness_email is not None:
            witness.witness_email = data.witness_email
        if data.read_on_text is not None:
            witness.read_on_text = data.read_on_text
        if data.read_off_text is not None:
            witness.read_off_text = data.read_off_text

        if data.actual_start_time is not None:
            witness.actual_start_time = _normalize_time_string(data.actual_start_time)
        if data.actual_end_time is not None:
            witness.actual_end_time = _normalize_time_string(data.actual_end_time)
        if data.read_on_time is not None:
            witness.read_on_time = _normalize_time_string(data.read_on_time)
        if data.read_off_time is not None:
            witness.read_off_time = _normalize_time_string(data.read_off_time)

        if getattr(data, "replace_videos", False):
            keep_ids = {v.id for v in data.videos if v.id and not v.delete}
            existing_videos = db.query(WitnessVideos).filter(
                WitnessVideos.wit_no == witness.id,
                ~WitnessVideos.is_archived,
            ).all()
            for ev in existing_videos:
                if ev.id not in keep_ids:
                    ev.is_archived = True
                    ev.last_modified_at = now
                    ev.last_modified_by = entered_by

        for item in data.videos:
            if item.delete and item.id:
                vid = db.query(WitnessVideos).filter(
                    WitnessVideos.id == item.id,
                    WitnessVideos.wit_no == witness.id,
                    ~WitnessVideos.is_archived,
                ).first()
                if vid:
                    vid.is_archived = True
                    vid.last_modified_at = now
                    vid.last_modified_by = entered_by
                continue

            if item.id:
                vid = db.query(WitnessVideos).filter(
                    WitnessVideos.id == item.id,
                    WitnessVideos.wit_no == witness.id,
                    ~WitnessVideos.is_archived,
                ).first()
                if not vid:
                    continue

                vid.last_modified_at = now
                vid.last_modified_by = entered_by
                if item.start_time is not None:
                    vid.start_time = _normalize_time_string(item.start_time)
                if item.end_time is not None:
                    vid.end_time = _normalize_time_string(item.end_time)
                
                item_dict = item.model_dump(exclude_unset=True)
                
                if 'file_index' in item_dict:
                    if item.file_index is not None:
                        if 0 <= item.file_index < len(files):
                            file_name, file_path = await save_video_file(files[item.file_index], "witness_videos")
                            vid.file_name = file_name
                            vid.file_path = file_path
                    else:
                        vid.file_name = None
                        vid.file_path = None
                continue

            start_time_str = _normalize_time_string(item.start_time)
            end_time_str = _normalize_time_string(item.end_time)
            file_name = None
            file_path = None
            if item.file_index is not None and 0 <= item.file_index < len(files):
                file_name, file_path = await save_video_file(
                    files[item.file_index], "witness_videos"
                )
            new_vid = WitnessVideos(
                wit_no=witness.id,
                job_no=witness.job_no,
                start_time=start_time_str,
                end_time=end_time_str,
                file_name=file_name,
                file_path=file_path,
                entered_at=now,
                entered_by=entered_by,
                last_modified_at=now,
                last_modified_by=entered_by,
            )
            db.add(new_vid)

        db.commit()

        witness_out: Witnesses = (
            db.query(Witnesses)
            .options(
                joinedload(Witnesses.witness_vid),
                with_loader_criteria(
                    WitnessVideos, WitnessVideos.is_archived == False, include_aliases=True
                ),
            )
            .filter(Witnesses.id == witness.id)
            .first()
        )
        witness_out_data = WitnessSchema.model_validate(witness_out).model_dump(mode="json")

        logger.info(f"Witness + videos saved successfully for witness_id {data.witness_id}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Witness + videos saved successfully",
                "success": True,
                "result": witness_out_data,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving witness/videos: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to save witness/videos: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def delete_witness_by_id(witness_id: int, db: Session) -> JSONResponse:
    entered_by = get_context("entered_by") or 0
    now = datetime.utcnow()

    try:
        witness: Optional[Witnesses] = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            ~Witnesses.is_archived,
        ).first()
        if not witness:
            logger.error(f"Witness with id {witness_id} not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Witness with id {witness_id} not found",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        videos = db.query(WitnessVideos).filter(
            WitnessVideos.wit_no == witness_id,
            ~WitnessVideos.is_archived,
        ).all()
        for v in videos:
            v.is_archived = True
            v.last_modified_at = now
            v.last_modified_by = entered_by

        witness.is_archived = True
        witness.last_modified_at = now
        witness.last_modified_by = entered_by

        db.commit()

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Witness archived successfully",
                "success": True,
                "result": {"witness_id": witness_id, "archived_videos": len(videos)},
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error archiving witness {witness_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to archive witness: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
