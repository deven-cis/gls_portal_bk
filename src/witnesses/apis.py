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
from src.core.timezone_utils import get_timezone_now
from src.jobs.models import Jobs
from src.jobs_tasks.models import JobsTasks
from src.cases.models import Cases

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
        current_rsrc_no = get_context("rsrc_no")
        witnesses: List[Witnesses] = (
            db.query(Witnesses)
            .join(Jobs, Witnesses.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .options(
                joinedload(Witnesses.witness_vid)
            )
            .filter(
                Witnesses.job_no == job_no,
                Witnesses.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no
            )
            .all()
        )

        data = [WitnessSchema.model_validate(w).model_dump(mode="json") for w in witnesses]
        logger.info(f"Found {len(data)} witnesses for job_no {job_no}")

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Found {len(data)} witnesses",
                "success": True,
                "result": data,
            },
            status_code=status.HTTP_200_OK,
        )

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
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        # Validate job exists and resource has access
        job = (
            db.query(Jobs.job_no, Cases.case_no, Cases.case_short_name, Cases.case_number)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Jobs.job_no == data.job_no,
                Jobs.is_archived == False,
                Cases.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not job:
            logger.error(f"Job with job_no {data.job_no} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {data.job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Create witness with direct assignment
        witness = Witnesses(
            job_no=data.job_no,
            witness_name=data.witness_name,
            read_on_text=(
                f"We are now on the record at [Time] on [Date]. This is the [Type] deposition of "
                f"{data.witness_name} in the matter of {job.case_short_name} case number {job.case_number}"
            ),
            read_off_text=(
                f"We are now off the record at [Time]. This concludes the deposition of {data.witness_name}"
            ),
            entered_by=current_rsrc_no,
            last_modified_by=current_rsrc_no,
            entered_at=now,
            last_modified_at=now
        )
        db.add(witness)
        db.commit()
        db.refresh(witness)

        witness_data = WitnessCreateSchema.model_validate(witness).model_dump(mode="json")
        logger.info(f"Witness {data.witness_name} created successfully for job {data.job_no}")

        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Witness created successfully",
                "success": True,
                "result": witness_data
            },
            status_code=status.HTTP_201_CREATED
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating witness: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to create witness: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        

async def update_witness_name(
    witness_id: int,
    payload: WitnessNameUpdateSchema,
    db: Session,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        name = (payload.witness_name or "").strip()
        if not name:
            logger.error("Witness name cannot be empty")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Witness name cannot be empty",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )

        witness = (
            db.query(Witnesses)
            .join(Jobs, Witnesses.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Witnesses.id == witness_id,
                Witnesses.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not witness:
            logger.error(f"Witness with id {witness_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Witness with id {witness_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Update via setattr
        update_payload = {
            "witness_name": name,
            "last_modified_at": now,
            "last_modified_by": current_rsrc_no
        }
        for key, value in update_payload.items():
            setattr(witness, key, value)

        db.add(witness)
        db.commit()
        db.refresh(witness)

        witness_data = WitnessSchema.model_validate(witness).model_dump(mode="json")
        logger.info(f"Witness name updated successfully for witness_id {witness_id}")

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Witness name updated successfully",
                "success": True,
                "result": witness_data
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating witness name {witness_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update witness name: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def save_witness_and_videos(
    payload: str,
    files: List[UploadFile],
    db: Session,
) -> JSONResponse:
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
                "result": {}
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        if not data.witness_id:
            logger.error("Witness ID is required for save/update")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "witness_id is required for save/update",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate witness with access control
        witness = (
            db.query(Witnesses)
            .join(Jobs, Witnesses.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Witnesses.id == data.witness_id,
                Witnesses.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not witness:
            logger.error(f"Witness with id {data.witness_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Witness with id {data.witness_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        if witness.job_no != data.job_no:
            logger.error(f"job_no mismatch for witness {witness.id} (expected {witness.job_no}, got {data.job_no})")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": f"job_no mismatch for witness {witness.id} (expected {witness.job_no}, got {data.job_no})",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Update witness text fields via setattr
        if data.witness_name is not None:
            new_name = str(data.witness_name).strip()
            if not new_name:
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "witness_name cannot be empty",
                        "success": False,
                        "result": {}
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            witness.witness_name = new_name

        # Time fields with normalization
        time_fields = {
            "actual_start_time": data.actual_start_time,
            "actual_end_time": data.actual_end_time,
            "read_on_time": data.read_on_time,
            "read_off_time": data.read_off_time
        }
        for field, value in time_fields.items():
            if value is not None:
                setattr(witness, field, _normalize_time_string(value))

        # Plain text fields
        text_fields = {
            "witness_email": data.witness_email,
            "read_on_text": data.read_on_text,
            "read_off_text": data.read_off_text
        }
        for field, value in text_fields.items():
            if value is not None:
                setattr(witness, field, value)

        # Replace videos — archive all not in keep list
        if getattr(data, "replace_videos", False):
            keep_ids = {v.id for v in data.videos if v.id and not v.delete}
            existing_videos = (
                db.query(WitnessVideos)
                .filter(
                    WitnessVideos.wit_no == witness.id,
                    WitnessVideos.is_archived == False
                )
                .all()
            )
            for ev in existing_videos:
                if ev.id not in keep_ids:
                    ev.is_archived = True
                    ev.last_modified_at = now
                    ev.last_modified_by = current_rsrc_no

        # Process video items
        for item in data.videos:
            # Delete video
            if item.delete and item.id:
                vid = (
                    db.query(WitnessVideos)
                    .filter(
                        WitnessVideos.id == item.id,
                        WitnessVideos.wit_no == witness.id,
                        WitnessVideos.is_archived == False
                    )
                    .first()
                )
                if vid:
                    vid.is_archived = True
                    vid.last_modified_at = now
                    vid.last_modified_by = current_rsrc_no
                continue

            # Update existing video
            if item.id:
                vid = (
                    db.query(WitnessVideos)
                    .filter(
                        WitnessVideos.id == item.id,
                        WitnessVideos.wit_no == witness.id,
                        WitnessVideos.is_archived == False
                    )
                    .first()
                )
                if not vid:
                    continue

                update_vid = {
                    "last_modified_at": now,
                    "last_modified_by": current_rsrc_no
                }
                if item.start_time is not None:
                    update_vid["start_time"] = _normalize_time_string(item.start_time)
                if item.end_time is not None:
                    update_vid["end_time"] = _normalize_time_string(item.end_time)

                item_dict = item.model_dump(exclude_unset=True)
                if 'file_index' in item_dict:
                    if item.file_index is not None and 0 <= item.file_index < len(files):
                        update_vid["file_name"], update_vid["file_path"] = await save_video_file(
                            files[item.file_index], "witness_videos"
                        )
                    else:
                        update_vid["file_name"] = None
                        update_vid["file_path"] = None

                for key, value in update_vid.items():
                    setattr(vid, key, value)
                continue

            # Create new video
            file_name, file_path = (
                await save_video_file(files[item.file_index], "witness_videos")
                if item.file_index is not None and 0 <= item.file_index < len(files)
                else (None, None)
            )
            new_vid = WitnessVideos(
                wit_no=witness.id,
                job_no=witness.job_no,
                start_time=_normalize_time_string(item.start_time),
                end_time=_normalize_time_string(item.end_time),
                file_name=file_name,
                file_path=file_path,
                entered_at=now,
                entered_by=current_rsrc_no,
                last_modified_at=now,
                last_modified_by=current_rsrc_no
            )
            db.add(new_vid)

        witness.last_modified_at = now
        witness.last_modified_by = current_rsrc_no
        db.add(witness)
        db.commit()
        db.refresh(witness)

        # Fetch final witness with videos
        witness_out = (
            db.query(Witnesses)
            .options(
                joinedload(Witnesses.witness_vid),
                with_loader_criteria(
                    WitnessVideos,
                    WitnessVideos.is_archived == False,
                    include_aliases=True
                )
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
                "result": witness_out_data
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving witness/videos: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to save witness/videos: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



async def delete_witness_by_id(witness_id: int, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        witness = (
            db.query(Witnesses)
            .join(Jobs, Witnesses.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Witnesses.id == witness_id,
                Witnesses.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not witness:
            logger.error(f"Witness with id {witness_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Witness with id {witness_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Bulk archive associated videos
        archived_videos = db.query(WitnessVideos).filter(
            WitnessVideos.wit_no == witness_id,
            WitnessVideos.is_archived == False
        ).update(
            {
                "is_archived": True,
                "last_modified_at": now,
                "last_modified_by": current_rsrc_no
            },
            synchronize_session=False
        )

        # Archive witness
        witness.is_archived = True
        witness.last_modified_at = now
        witness.last_modified_by = current_rsrc_no
        db.add(witness)
        db.commit()

        logger.info(f"Witness {witness_id} and {archived_videos} video(s) archived successfully")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Witness archived successfully",
                "success": True,
                "result": {
                    "witness_id": witness_id,
                    "archived_videos": archived_videos
                }
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error archiving witness {witness_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to archive witness: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )