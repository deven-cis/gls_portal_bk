from typing import Any, Dict, List, Optional, Union
import json
import uuid
from jose import jwt
from datetime import timedelta, time as dt_time, datetime
from pathlib import Path
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload, with_loader_criteria
from src.core.context import get_context, set_context
from src.core.logger import logger
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.uploaded_videos.models import UploadedVideos
from src.uploaded_videos.services import cleanup_expired_uploaded_videos
from src.core.file_utils import (
    append_upload_chunk_to_file,
    extract_video_metadata,
    get_temp_video_upload_path,
    promote_video_to_final_storage,
    save_video_file,
    validate_video_filename,
)
from src.witnesses.schema import (
    CreateWitnessFrontSchema,
    WitnessCreateSchema,
    WitnessNameUpdateSchema,
    WitnessVideoUploadPauseSchema,
    WitnessVideoUploadResumeSchema,
    WitnessVideoUploadCancelSchema,
    WitnessSaveAllPayloadSchema,
    WitnessSchema,
    WitnessVideoUploadCompleteSchema,
    WitnessVideoUploadInitSchema,
)
from src.core.config import config
from src.core.storage_urls import build_video_download_url
from src.core.rbac import get_current_user_role, is_admin_role
from src.core.video_merge import build_witness_merged_video_output_path, delete_file_if_exists
from src.core.celery_config import celery_app
from src.core.timezone_utils import get_timezone_now
from src.jobs.models import Jobs
from src.jobs_tasks.models import JobsTasks
from src.cases.models import Cases


def _create_download_token(*, token_type: str, rsrc_no: int, rsrc_role: Optional[str] = None, video_id: Optional[int] = None, witness_id: Optional[int] = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=5)
    payload = {
        "rsrc_no": rsrc_no,
        "rsrc_role": rsrc_role,
        "type": token_type,
        "exp": expire,
    }
    if video_id is not None:
        payload["video_id"] = video_id
    if witness_id is not None:
        payload["witness_id"] = witness_id
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def _create_video_download_token(video_id: int, rsrc_no: int, rsrc_role: Optional[str] = None) -> str:
    return _create_download_token(
        token_type="witness_video_download",
        video_id=video_id,
        rsrc_no=rsrc_no,
        rsrc_role=rsrc_role,
    )


def _create_complete_video_download_token(witness_id: int, rsrc_no: int, rsrc_role: Optional[str] = None) -> str:
    return _create_download_token(
        token_type="witness_complete_video_download",
        witness_id=witness_id,
        rsrc_no=rsrc_no,
        rsrc_role=rsrc_role,
    )


def _decode_download_token(token: str, expected_type: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM],
            options={"require_exp": True},
        )
        if payload.get("type") != expected_type:
            return None
        return payload
    except Exception:
        return None


def _decode_video_download_token(token: str) -> Optional[dict]:
    return _decode_download_token(token, "witness_video_download")


def _decode_complete_video_download_token(token: str) -> Optional[dict]:
    return _decode_download_token(token, "witness_complete_video_download")


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


def _build_video_fields_from_upload(upload_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file_name": upload_data.get("file_name"),
        "file_path": upload_data.get("file_path"),
        "file_size": upload_data.get("file_size"),
        "duration_seconds": upload_data.get("duration_seconds"),
        "timecode": upload_data.get("timecode"),
    }


def _build_upload_response(upload: UploadedVideos) -> Dict[str, Any]:
    return {
        "upload_id": upload.upload_id,
        "file_name": upload.original_file_name,
        "file_path": upload.final_file_path or upload.temp_file_path,
        "file_size": upload.file_size or upload.expected_file_size,
        "bytes_received": upload.bytes_received,
        "received_chunks": upload.received_chunks,
        "total_chunks": upload.total_chunks,
        "duration_seconds": float(upload.duration_seconds) if upload.duration_seconds is not None else None,
        "timecode": upload.timecode,
        "format_name": upload.format_name,
        "status": upload.status,
    }


def _get_upload_record(
    upload_id: str,
    db: Session,
    lock_for_update: bool = False,
) -> UploadedVideos:
    query = (
        db.query(UploadedVideos)
        .filter(
            UploadedVideos.upload_id == upload_id,
            UploadedVideos.is_archived == False,
        )
    )
    if lock_for_update:
        query = query.with_for_update()

    upload = query.first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {upload_id} not found",
        )
    return upload


def _consume_completed_upload(
    upload_id: str,
    db: Session,
    now,
    current_rsrc_no: int,
    witness_video_id: Optional[int] = None,
) -> Dict[str, Any]:
    upload = _get_upload_record(upload_id, db, lock_for_update=True)
    if upload.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload {upload_id} is not ready to attach",
        )
    if upload.attached_at is not None or upload.status == "attached":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upload {upload_id} has already been attached",
        )
    if not upload.temp_file_path or not Path(upload.temp_file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload file for {upload_id} was not found",
        )

    upload.status = "attaching"
    upload.last_modified_at = now
    upload.last_modified_by = current_rsrc_no
    db.add(upload)
    db.flush()

    stored_file_name, final_file_path = promote_video_to_final_storage(
        source_path=upload.temp_file_path,
        file_ext=upload.file_ext,
        subfolder="witness_videos",
    )

    upload.stored_file_name = stored_file_name
    upload.final_file_path = final_file_path
    upload.temp_file_path = None
    upload.status = "attached"
    upload.attached_at = now
    upload.witness_video_id = witness_video_id
    upload.last_modified_at = now
    upload.last_modified_by = current_rsrc_no

    return {
        "file_name": upload.original_file_name,
        "file_path": final_file_path,
        "file_size": upload.file_size,
        "duration_seconds": float(upload.duration_seconds) if upload.duration_seconds is not None else None,
        "timecode": upload.timecode,
    }


async def trigger_uploaded_video_cleanup(db: Session) -> JSONResponse:
    now = get_timezone_now()
    app_env = (config.APP_ENV or "").lower().strip()

    if app_env in {"production", "staging"}:
        logger.warning(
            "Blocked manual uploaded video cleanup endpoint in %s environment",
            app_env,
        )
        return JSONResponse(
            content={
                "status_code": status.HTTP_403_FORBIDDEN,
                "message": "Manual cleanup endpoint is disabled in production-like environments",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    logger.warning(
        "Manual uploaded video cleanup endpoint invoked in %s environment",
        app_env or "unknown",
    )
    try:
        result = cleanup_expired_uploaded_videos(db, now, source="api-manual")
        db.commit()
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Expired uploaded video cleanup executed successfully",
                "success": True,
                "result": result,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Manual uploaded video cleanup failed: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to run uploaded video cleanup: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def init_witness_video_upload(data: WitnessVideoUploadInitSchema, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        cleanup_expired_uploaded_videos(db, now, source="api-init")

        file_ext = validate_video_filename(data.file_name)
        upload_id = str(uuid.uuid4())
        upload = UploadedVideos(
            upload_id=upload_id,
            original_file_name=data.file_name,
            content_type=data.content_type,
            file_ext=file_ext,
            expected_file_size=data.file_size,
            total_chunks=data.total_chunks,
            received_chunks=0,
            bytes_received=0,
            status="initialized",
            expires_at=now + timedelta(hours=24),
            entered_at=now,
            entered_by=current_rsrc_no,
            last_modified_at=now,
            last_modified_by=current_rsrc_no,
        )
        db.add(upload)
        db.commit()

        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Video upload initialized successfully",
                "success": True,
                "result": {
                    "upload_id": upload.upload_id,
                    "file_name": upload.original_file_name,
                    "file_size": upload.expected_file_size,
                    "total_chunks": upload.total_chunks,
                    "status": upload.status,
                },
            },
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException as exc:
        return JSONResponse(
            content={
                "status_code": exc.status_code,
                "message": exc.detail,
                "success": False,
                "result": {},
            },
            status_code=exc.status_code,
        )
    except Exception as exc:
        logger.error("Failed to initialize witness video upload: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to initialize witness video upload: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def upload_witness_video_chunk(
    upload_id: str,
    chunk_number: int,
    total_chunks: int,
    file: UploadFile,
    db: Session,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        upload = _get_upload_record(upload_id, db, lock_for_update=True)

        if upload.status == "paused":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload is paused. Resume it before sending more chunks.",
            )
        if upload.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload has already been cancelled.",
            )
        if upload.status in {"completed", "attaching", "attached"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Upload is already in '{upload.status}' state.",
            )

        file_ext = validate_video_filename(file.filename or upload.original_file_name)
        if file_ext != upload.file_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded chunk file extension does not match the initialized upload",
            )

        expected_chunk = int(upload.received_chunks or 0)
        if chunk_number != expected_chunk:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Expected chunk_number {expected_chunk}, got {chunk_number}",
            )

        if upload.total_chunks is None:
            upload.total_chunks = total_chunks
        elif int(upload.total_chunks) != int(total_chunks):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="total_chunks does not match the initialized upload session",
            )

        temp_file_path = Path(upload.temp_file_path) if upload.temp_file_path else get_temp_video_upload_path(upload.upload_id, upload.file_ext)
        if chunk_number == 0 and temp_file_path.exists():
            temp_file_path.unlink()

        bytes_written = await append_upload_chunk_to_file(temp_file_path, file, mode="ab")

        upload.temp_file_path = str(temp_file_path)
        upload.bytes_received = int(upload.bytes_received or 0) + bytes_written
        upload.received_chunks = expected_chunk + 1
        upload.status = "uploading" if upload.received_chunks < upload.total_chunks else "uploaded"
        upload.last_modified_at = now
        upload.last_modified_by = current_rsrc_no
        db.add(upload)
        db.commit()

        result = {
            "upload_id": upload.upload_id,
            "chunk_number": chunk_number,
            "received_chunks": upload.received_chunks,
            "total_chunks": upload.total_chunks,
            "bytes_received": upload.bytes_received,
            "status": upload.status,
        }
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Video chunk uploaded successfully",
                "success": True,
                "result": result,
            },
            status_code=status.HTTP_200_OK,
        )
    except HTTPException as exc:
        return JSONResponse(
            content={
                "status_code": exc.status_code,
                "message": exc.detail,
                "success": False,
                "result": {},
            },
            status_code=exc.status_code,
        )
    except Exception as exc:
        logger.error("Failed to upload witness video chunk: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to upload video chunk: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def complete_witness_video_upload(data: WitnessVideoUploadCompleteSchema, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        upload = _get_upload_record(data.upload_id, db, lock_for_update=True)

        if upload.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload has already been cancelled",
            )
        if upload.status == "paused":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload is paused. Resume it before completing.",
            )

        if upload.total_chunks is None or upload.received_chunks != upload.total_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload is incomplete ({upload.received_chunks}/{upload.total_chunks} chunks received)",
            )
        if not upload.temp_file_path or not Path(upload.temp_file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Uploaded temp file is no longer available. The upload may have been cancelled.",
            )

        metadata = await extract_video_metadata(upload.temp_file_path)
        if not metadata.get("file_size"):
            temp_file = Path(upload.temp_file_path)
            if not temp_file.exists():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Uploaded temp file is no longer available. The upload may have been cancelled.",
                )
            metadata["file_size"] = temp_file.stat().st_size

        upload.file_size = metadata.get("file_size")
        upload.duration_seconds = metadata.get("duration_seconds")
        upload.timecode = metadata.get("timecode")
        upload.format_name = metadata.get("format_name")
        upload.status = "completed"
        upload.last_modified_at = now
        upload.last_modified_by = current_rsrc_no
        db.add(upload)
        db.commit()

        result = _build_upload_response(upload)
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Video upload completed successfully",
                "success": True,
                "result": result,
            },
            status_code=status.HTTP_200_OK,
        )
    except HTTPException as exc:
        return JSONResponse(
            content={
                "status_code": exc.status_code,
                "message": exc.detail,
                "success": False,
                "result": {},
            },
            status_code=exc.status_code,
        )
    except Exception as exc:
        logger.error("Failed to complete witness video upload: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to complete video upload: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def pause_witness_video_upload(data: WitnessVideoUploadPauseSchema, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        upload = _get_upload_record(data.upload_id, db, lock_for_update=True)

        if upload.attached_at is not None or upload.status in {"attached", "attaching", "completed"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Upload in '{upload.status}' state cannot be paused",
            )
        if upload.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cancelled uploads cannot be paused",
            )

        upload.status = "paused"
        upload.last_modified_at = now
        upload.last_modified_by = current_rsrc_no
        db.add(upload)
        db.commit()

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Video upload paused successfully",
                "success": True,
                "result": _build_upload_response(upload),
            },
            status_code=status.HTTP_200_OK,
        )
    except HTTPException as exc:
        return JSONResponse(
            content={
                "status_code": exc.status_code,
                "message": exc.detail,
                "success": False,
                "result": {},
            },
            status_code=exc.status_code,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Failed to pause witness video upload: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to pause video upload: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def resume_witness_video_upload(data: WitnessVideoUploadResumeSchema, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        upload = _get_upload_record(data.upload_id, db, lock_for_update=True)

        if upload.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cancelled uploads cannot be resumed",
            )
        if upload.status in {"completed", "attaching", "attached"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Upload in '{upload.status}' state cannot be resumed",
            )

        upload.status = "uploading" if int(upload.received_chunks or 0) > 0 else "initialized"
        upload.last_modified_at = now
        upload.last_modified_by = current_rsrc_no
        db.add(upload)
        db.commit()

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Video upload resumed successfully",
                "success": True,
                "result": _build_upload_response(upload),
            },
            status_code=status.HTTP_200_OK,
        )
    except HTTPException as exc:
        return JSONResponse(
            content={
                "status_code": exc.status_code,
                "message": exc.detail,
                "success": False,
                "result": {},
            },
            status_code=exc.status_code,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Failed to resume witness video upload: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to resume video upload: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def cancel_witness_video_upload(data: WitnessVideoUploadCancelSchema, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        upload = _get_upload_record(data.upload_id, db, lock_for_update=True)

        if upload.attached_at is not None or upload.status == "attached":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attached uploads cannot be cancelled",
            )

        deleted_files = 0
        for file_path in [upload.temp_file_path, upload.final_file_path]:
            if file_path and Path(file_path).exists():
                try:
                    Path(file_path).unlink()
                    deleted_files += 1
                except Exception:
                    logger.warning("Failed to delete cancelled upload file %s", file_path, exc_info=True)

        upload.temp_file_path = None
        upload.final_file_path = None
        upload.status = "cancelled"
        upload.is_archived = True
        upload.last_modified_at = now
        upload.last_modified_by = current_rsrc_no
        db.add(upload)
        db.commit()

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Video upload cancelled successfully",
                "success": True,
                "result": {
                    "upload_id": upload.upload_id,
                    "status": upload.status,
                    "deleted_files": deleted_files,
                },
            },
            status_code=status.HTTP_200_OK,
        )
    except HTTPException as exc:
        return JSONResponse(
            content={
                "status_code": exc.status_code,
                "message": exc.detail,
                "success": False,
                "result": {},
            },
            status_code=exc.status_code,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Failed to cancel witness video upload: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to cancel video upload: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def get_witnesses_list_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context("rsrc_no")
        witnesses: List[Witnesses] = (
            db.query(Witnesses)
            .join(Jobs, Witnesses.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .options(
                joinedload(Witnesses.witness_vid),
                with_loader_criteria(
                    WitnessVideos,
                    WitnessVideos.is_archived == False,
                    include_aliases=True
                )
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


def _get_accessible_witness(witness_id: int, db: Session):
    current_rsrc_no = get_context("rsrc_no")
    current_role = get_current_user_role()
    if current_rsrc_no is None:
        return None, JSONResponse(
            content={
                "status_code": status.HTTP_403_FORBIDDEN,
                "message": "Unable to determine current resource context",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    query = (
        db.query(Witnesses)
        .join(Jobs, Witnesses.job_no == Jobs.job_no)
        .join(Cases, Jobs.case_no == Cases.case_no)
        .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
        .filter(
            Witnesses.id == witness_id,
            Witnesses.is_archived == False,
            Jobs.is_archived == False,
            Cases.is_archived == False,
            JobsTasks.is_archived == False,
        )
    )

    if not is_admin_role(current_role):
        query = query.filter(JobsTasks.rsrc_no == current_rsrc_no)

    witness = query.first()
    if not witness:
        return None, JSONResponse(
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "Witness not found or access denied",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return witness, None


def _build_witness_merge_result(witness: Witnesses) -> Dict[str, Any]:
    return {
        "witness_id": witness.id,
        "job_no": witness.job_no,
        "merge_status": witness.merge_status or "not_requested",
        "merge_error": witness.merge_error,
        "merge_requested_at": witness.merge_requested_at.isoformat() if witness.merge_requested_at else None,
        "merge_completed_at": witness.merge_completed_at.isoformat() if witness.merge_completed_at else None,
        "merged_video_name": witness.merged_video_name,
        "merged_video_path": witness.merged_video_path,
        "merged_video_size": int(witness.merged_video_size) if witness.merged_video_size is not None else None,
        "merged_duration": float(witness.merged_duration) if witness.merged_duration is not None else None,
    }


def _reset_witness_merge_fields(
    witness: Witnesses,
    now: datetime,
    modified_by: Optional[int],
    *,
    status_value: str = "not_requested",
    error_message: Optional[str] = None,
) -> Optional[str]:
    previous_path = witness.merged_video_path
    witness.merged_video_path = None
    witness.merged_video_name = None
    witness.merged_video_size = None
    witness.merged_duration = None
    witness.merge_status = status_value
    witness.merge_error = error_message
    witness.merge_requested_at = None if status_value == "not_requested" else witness.merge_requested_at
    witness.merge_completed_at = None
    witness.last_modified_at = now
    if modified_by is not None:
        witness.last_modified_by = modified_by
    return previous_path


def _mark_witness_merge_requested(witness: Witnesses, now: datetime, requested_by: Optional[int]) -> None:
    witness.merge_status = "pending"
    witness.merge_error = None
    witness.merge_requested_at = now
    witness.merge_completed_at = None
    witness.last_modified_at = now
    if requested_by is not None:
        witness.last_modified_by = requested_by


def _get_accessible_witness_video(video_id: int, db: Session):
    current_rsrc_no = get_context("rsrc_no")
    current_role = get_current_user_role()
    if current_rsrc_no is None:
        return None, JSONResponse(
            content={
                "status_code": status.HTTP_403_FORBIDDEN,
                "message": "Unable to determine current resource context",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    query = (
        db.query(WitnessVideos)
        .join(Witnesses, WitnessVideos.wit_no == Witnesses.id)
        .join(Jobs, WitnessVideos.job_no == Jobs.job_no)
        .join(Cases, Jobs.case_no == Cases.case_no)
        .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
        .filter(
            WitnessVideos.id == video_id,
            WitnessVideos.is_archived == False,
            Witnesses.is_archived == False,
            Jobs.is_archived == False,
            Cases.is_archived == False,
            JobsTasks.is_archived == False,
        )
    )

    admin_access_enabled = is_admin_role(current_role)
    if not admin_access_enabled:
        query = query.filter(JobsTasks.rsrc_no == current_rsrc_no)
    else:
        logger.info(
            "Admin witness video access enabled for user %s (%s) on video %s",
            current_rsrc_no,
            current_role,
            video_id,
        )

    video = query.first()

    if not video or not video.file_path:
        return None, JSONResponse(
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "Video not found or access denied",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return video, None


async def get_witness_video_download_link(
    video_id: int,
    db: Session,
    request_base_url: Optional[str] = None,
) -> JSONResponse:
    """
    Build a browser-downloadable URL for a single witness video.
    URL generation is centralized so switching to CDN/S3 later needs minimal changes.
    """
    try:
        current_rsrc_no = get_context("rsrc_no")
        current_role = get_current_user_role()
        video, error_response = _get_accessible_witness_video(video_id, db)
        if error_response:
            return error_response

        if not str(video.file_path).startswith(("http://", "https://")):
            if not Path(video.file_path).exists():
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": "Video file is missing on server",
                        "success": False,
                        "result": {},
                    },
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        base_url = (request_base_url or '').rstrip('/')
        download_token = _create_video_download_token(video.id, current_rsrc_no, current_role)
        download_url = f"{base_url}/witnesses/videos/{video.id}/download?token={download_token}"

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Video download link generated successfully",
                "success": True,
                "result": {
                    "video_id": video.id,
                    "job_no": video.job_no,
                    "file_name": video.file_name or Path(video.file_path).name,
                    "download_url": download_url,
                    "storage_backend": (config.STORAGE_BACKEND or "local").strip().lower(),
                },
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error generating witness video download link: %s", str(e), exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to generate video download link: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def download_witness_video(
    video_id: int,
    db: Session,
    download_token: Optional[str] = None,
) -> Union[JSONResponse, FileResponse]:
    try:
        if not download_token:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": "Download token is required",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )

        token_payload = _decode_video_download_token(download_token)
        if not token_payload:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": "Invalid or expired download token",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if int(token_payload.get("video_id") or 0) != int(video_id):
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": "Download token does not match requested video",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )

        set_context(rsrc_no=token_payload.get("rsrc_no"), rsrc_role=token_payload.get("rsrc_role"))
        video, error_response = _get_accessible_witness_video(video_id, db)
        if error_response:
            return error_response

        if str(video.file_path).startswith(("http://", "https://")):
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Remote video downloads are not supported by this endpoint",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        file_path = Path(video.file_path)
        if not file_path.exists():
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Video file is missing on server",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        download_name = video.file_name or file_path.name
        media_type = "application/octet-stream"
        suffix = file_path.suffix.lower()
        if suffix in {".mp4", ".m4v"}:
            media_type = "video/mp4"
        elif suffix == ".webm":
            media_type = "video/webm"
        elif suffix == ".mov":
            media_type = "video/quicktime"
        elif suffix == ".avi":
            media_type = "video/x-msvideo"
        elif suffix == ".mkv":
            media_type = "video/x-matroska"

        return FileResponse(
            path=str(file_path),
            filename=download_name,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={download_name}"
            },
        )
    except Exception as e:
        logger.error("Error downloading witness video: %s", str(e), exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to download video: {str(e)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def request_witness_complete_video_merge(
    witness_id: int,
    db: Session,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        witness, error_response = _get_accessible_witness(witness_id, db)
        if error_response:
            return error_response

        witness = (
            db.query(Witnesses)
            .filter(Witnesses.id == witness.id)
            .with_for_update()
            .first()
        )
        if not witness:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Witness not found or access denied",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        videos = (
            db.query(WitnessVideos)
            .filter(
                WitnessVideos.wit_no == witness.id,
                WitnessVideos.is_archived == False,
            )
            .all()
        )
        available_videos = [video for video in videos if video.file_path and Path(video.file_path).exists()]
        if not available_videos:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "No saved witness videos are available to merge",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if witness.merge_status == 'completed' and witness.merged_video_path and Path(witness.merged_video_path).exists():
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Merged witness video is already available",
                    "success": True,
                    "result": _build_witness_merge_result(witness),
                },
                status_code=status.HTTP_200_OK,
            )

        if witness.merge_status in {'pending', 'processing'}:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_202_ACCEPTED,
                    "message": "Witness complete video is already being generated",
                    "success": True,
                    "result": _build_witness_merge_result(witness),
                },
                status_code=status.HTTP_202_ACCEPTED,
            )

        stale_path = None
        if witness.merged_video_path:
            stale_path = _reset_witness_merge_fields(witness, now, current_rsrc_no)
        _mark_witness_merge_requested(witness, now, current_rsrc_no)
        db.add(witness)
        db.commit()

        if stale_path:
            delete_file_if_exists(stale_path)

        celery_app.send_task(
            'src.witnesses.tasks.generate_witness_complete_video_task',
            args=[witness.id, current_rsrc_no],
        )
        db.refresh(witness)

        return JSONResponse(
            content={
                "status_code": status.HTTP_202_ACCEPTED,
                "message": "Witness complete video generation started",
                "success": True,
                "result": _build_witness_merge_result(witness),
            },
            status_code=status.HTTP_202_ACCEPTED,
        )
    except Exception as exc:
        db.rollback()
        logger.error('Failed to request witness complete video merge: %s', exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to request witness complete video merge: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def get_witness_complete_video_status(
    witness_id: int,
    db: Session,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        witness, error_response = _get_accessible_witness(witness_id, db)
        if error_response:
            return error_response

        if witness.merge_status == 'completed' and witness.merged_video_path and not Path(witness.merged_video_path).exists():
            _reset_witness_merge_fields(witness, now, current_rsrc_no, status_value='not_requested', error_message=None)
            db.add(witness)
            db.commit()
            db.refresh(witness)

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Witness complete video status retrieved successfully",
                "success": True,
                "result": _build_witness_merge_result(witness),
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.error('Failed to get witness complete video status: %s', exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get witness complete video status: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def get_witness_complete_video_download_link(
    witness_id: int,
    db: Session,
    request_base_url: Optional[str] = None,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        current_role = get_current_user_role()
        witness, error_response = _get_accessible_witness(witness_id, db)
        if error_response:
            return error_response

        if witness.merge_status != 'completed' or not witness.merged_video_path:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "Merged witness video is not ready yet",
                    "success": False,
                    "result": _build_witness_merge_result(witness),
                },
                status_code=status.HTTP_409_CONFLICT,
            )

        merged_path = Path(witness.merged_video_path)
        if not merged_path.exists():
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Merged witness video file is missing on server",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        base_url = (request_base_url or '').rstrip('/')
        download_token = _create_complete_video_download_token(witness.id, current_rsrc_no, current_role)
        download_url = f"{base_url}/witnesses/{witness.id}/complete-video/download?token={download_token}"

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Witness complete video download link generated successfully",
                "success": True,
                "result": {
                    **_build_witness_merge_result(witness),
                    "download_url": download_url,
                    "file_name": witness.merged_video_name or merged_path.name,
                },
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.error('Failed to generate witness complete video download link: %s', exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to generate witness complete video download link: {str(exc)}",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def download_witness_complete_video(
    witness_id: int,
    db: Session,
    download_token: Optional[str] = None,
) -> Union[JSONResponse, FileResponse]:
    try:
        if not download_token:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": "Download token is required",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )

        token_payload = _decode_complete_video_download_token(download_token)
        if not token_payload:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": "Invalid or expired download token",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if int(token_payload.get('witness_id') or 0) != int(witness_id):
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": "Download token does not match requested witness",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )

        set_context(rsrc_no=token_payload.get('rsrc_no'), rsrc_role=token_payload.get('rsrc_role'))
        witness, error_response = _get_accessible_witness(witness_id, db)
        if error_response:
            return error_response

        if witness.merge_status != 'completed' or not witness.merged_video_path:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "Merged witness video is not ready yet",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_409_CONFLICT,
            )

        file_path = Path(witness.merged_video_path)
        if not file_path.exists():
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Merged witness video file is missing on server",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        download_name = witness.merged_video_name or file_path.name
        return FileResponse(
            path=str(file_path),
            filename=download_name,
            media_type='video/mp4',
            headers={
                'Content-Disposition': f'attachment; filename={download_name}'
            },
        )
    except Exception as exc:
        logger.error('Failed to download witness complete video: %s', exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to download witness complete video: {str(exc)}",
                "success": False,
                "result": {},
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
        if not download_all:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "download_all is required",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        witness, error_response = _get_accessible_witness(witness_id, db)
        if error_response:
            return error_response
        if int(witness.job_no) != int(job_no):
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Witness does not belong to the requested job",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if witness.merge_status != 'completed' or not witness.merged_video_path:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "Merged witness video is not ready yet",
                    "success": False,
                    "result": _build_witness_merge_result(witness),
                },
                status_code=status.HTTP_409_CONFLICT,
            )

        merged_path = Path(witness.merged_video_path)
        if not merged_path.exists():
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Merged witness video file is missing on server",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        file_name = witness.merged_video_name or merged_path.name
        return FileResponse(
            path=str(merged_path),
            filename=file_name,
            media_type='video/mp4',
            headers={
                'Content-Disposition': f'attachment; filename={file_name}'
            },
        )
    except Exception as exc:
        logger.error('Error downloading witnesses complete video: %s', exc, exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to download witnesses complete video: {str(exc)}",
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
        logger.info("Saving witness and videos proccess-----------")
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
        video_structure_changed = False
        merge_artifact_to_delete = None

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
                    video_structure_changed = True

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
                    video_structure_changed = True
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
                if item.start_time is not None or item.end_time is not None or item.upload_token or 'file_index' in item_dict:
                    video_structure_changed = True
                if item.upload_token:
                    upload_data = _consume_completed_upload(
                        item.upload_token,
                        db,
                        now,
                        current_rsrc_no,
                        witness_video_id=vid.id,
                    )
                    update_vid.update(_build_video_fields_from_upload(upload_data))
                elif 'file_index' in item_dict:
                    if item.file_index is not None and 0 <= item.file_index < len(files):
                        file_name, file_path, metadata = await save_video_file(
                            files[item.file_index], "witness_videos"
                        )
                        update_vid["file_name"] = file_name
                        update_vid["file_path"] = file_path
                        update_vid["file_size"] = metadata.get("file_size")
                        update_vid["duration_seconds"] = metadata.get("duration_seconds")
                        update_vid["timecode"] = metadata.get("timecode")
                    else:
                        update_vid["file_name"] = None
                        update_vid["file_path"] = None
                        update_vid["file_size"] = None
                        update_vid["duration_seconds"] = None
                        update_vid["timecode"] = None

                for key, value in update_vid.items():
                    setattr(vid, key, value)
                continue

            # Create new video
            if item.upload_token:
                file_name = None
                file_path = None
                metadata = {}
            else:
                file_name, file_path, metadata = (
                    await save_video_file(files[item.file_index], "witness_videos")
                    if item.file_index is not None and 0 <= item.file_index < len(files)
                    else (None, None, {})
                )
            video_structure_changed = True
            new_vid = WitnessVideos(
                wit_no=witness.id,
                job_no=witness.job_no,
                start_time=_normalize_time_string(item.start_time),
                end_time=_normalize_time_string(item.end_time),
                file_name=file_name,
                file_path=file_path,
                file_size=metadata.get("file_size"),
                duration_seconds=metadata.get("duration_seconds"),
                timecode=metadata.get("timecode"),
                entered_at=now,
                entered_by=current_rsrc_no,
                last_modified_at=now,
                last_modified_by=current_rsrc_no
            )
            db.add(new_vid)
            db.flush()

            if item.upload_token:
                upload_data = _consume_completed_upload(
                    item.upload_token,
                    db,
                    now,
                    current_rsrc_no,
                    witness_video_id=new_vid.id,
                )
                new_vid.file_name = upload_data.get("file_name")
                new_vid.file_path = upload_data.get("file_path")
                new_vid.file_size = upload_data.get("file_size")
                new_vid.duration_seconds = upload_data.get("duration_seconds")
                new_vid.timecode = upload_data.get("timecode")

        if video_structure_changed:
            merge_artifact_to_delete = _reset_witness_merge_fields(witness, now, current_rsrc_no)

        witness.last_modified_at = now
        witness.last_modified_by = current_rsrc_no
        db.add(witness)
        db.commit()
        if merge_artifact_to_delete:
            delete_file_if_exists(merge_artifact_to_delete)
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

        merged_file_to_delete = witness.merged_video_path

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
        if merged_file_to_delete:
            delete_file_if_exists(merged_file_to_delete)

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
