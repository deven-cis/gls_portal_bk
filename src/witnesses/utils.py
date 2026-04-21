from typing import Any, Dict, Optional
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from jose import jwt
from sqlalchemy.orm import Session

from src.cases.models import Cases
from src.core.config import config
from src.core.context import get_context
from src.core.rbac import get_current_user_role, is_admin_role
from src.core.storage.storage_prefixes import temp_video_prefix, witness_video_prefix
from src.core.storage.storage_service import storage_service
from src.uploaded_videos.models import UploadedVideos
from src.witness_videos.models import WitnessVideos
from src.witnesses.models import Witnesses
from src.jobs.models import Jobs
from src.jobs_tasks.models import JobsTasks


def create_download_token(
    *,
    token_type: str,
    rsrc_no: int,
    rsrc_role: Optional[str] = None,
    video_id: Optional[int] = None,
    witness_id: Optional[int] = None,
) -> str:
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


def create_video_download_token(video_id: int, rsrc_no: int, rsrc_role: Optional[str] = None) -> str:
    return create_download_token(
        token_type="witness_video_download",
        video_id=video_id,
        rsrc_no=rsrc_no,
        rsrc_role=rsrc_role,
    )


def create_complete_video_download_token(
    witness_id: int,
    rsrc_no: int,
    rsrc_role: Optional[str] = None,
) -> str:
    return create_download_token(
        token_type="witness_complete_video_download",
        witness_id=witness_id,
        rsrc_no=rsrc_no,
        rsrc_role=rsrc_role,
    )


def decode_download_token(token: str, expected_type: str) -> Optional[dict]:
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


def decode_video_download_token(token: str) -> Optional[dict]:
    return decode_download_token(token, "witness_video_download")


def decode_complete_video_download_token(token: str) -> Optional[dict]:
    return decode_download_token(token, "witness_complete_video_download")


def normalize_time_string(value: Optional[str]) -> Optional[str]:
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


def build_video_fields_from_upload(upload_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file_name": upload_data.get("file_name"),
        "file_path": upload_data.get("file_path"),
        "file_size": upload_data.get("file_size"),
        "duration_seconds": upload_data.get("duration_seconds"),
        "timecode": upload_data.get("timecode"),
    }


def build_upload_response(upload: UploadedVideos) -> Dict[str, Any]:
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
        "upload_strategy": upload.upload_strategy or "backend_chunked",
    }


def get_upload_record(
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


def consume_completed_upload(
    upload_id: str,
    db: Session,
    now,
    current_rsrc_no: int,
    witness_video_id: Optional[int] = None,
) -> Dict[str, Any]:
    upload = get_upload_record(upload_id, db, lock_for_update=True)
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
    if not upload.temp_file_path or not storage_service.exists(upload.temp_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload file for {upload_id} was not found",
        )

    upload.status = "attaching"
    upload.last_modified_at = now
    upload.last_modified_by = current_rsrc_no
    db.add(upload)
    db.flush()

    storage_subfolder = "witness_videos"
    if witness_video_id:
        witness_video = db.query(WitnessVideos).filter(WitnessVideos.id == witness_video_id).first()
        if witness_video:
            storage_subfolder = witness_video_prefix(
                rsrc_no=current_rsrc_no,
                job_no=witness_video.job_no,
                witness_id=witness_video.wit_no,
                video_id=witness_video.id,
            )

    stored_file = storage_service.copy(
        upload.temp_file_path,
        subfolder=storage_subfolder,
        file_name=upload.original_file_name,
        content_type=upload.content_type,
        delete_source=True,
    )

    upload.stored_file_name = stored_file.file_name
    upload.final_file_path = stored_file.key
    upload.temp_file_path = None
    upload.status = "attached"
    upload.attached_at = now
    upload.witness_video_id = witness_video_id
    upload.last_modified_at = now
    upload.last_modified_by = current_rsrc_no

    return {
        "file_name": upload.original_file_name,
        "file_path": stored_file.key,
        "file_size": upload.file_size,
        "duration_seconds": float(upload.duration_seconds) if upload.duration_seconds is not None else None,
        "timecode": upload.timecode,
    }


def get_accessible_witness(witness_id: int, db: Session):
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


def build_witness_merge_result(witness: Witnesses) -> Dict[str, Any]:
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


def stored_path_exists(path: Optional[str]) -> bool:
    return storage_service.exists(path)


def delete_stored_path(path: Optional[str]) -> bool:
    return storage_service.delete(path)


def reset_witness_merge_fields(
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


def mark_witness_merge_requested(witness: Witnesses, now: datetime, requested_by: Optional[int]) -> None:
    witness.merge_status = "pending"
    witness.merge_error = None
    witness.merge_requested_at = now
    witness.merge_completed_at = None
    witness.last_modified_at = now
    if requested_by is not None:
        witness.last_modified_by = requested_by


def get_accessible_witness_video(video_id: int, db: Session):
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


def finalize_completed_upload_storage(upload: UploadedVideos, current_rsrc_no: int) -> None:
    if not storage_service.is_s3:
        return

    stored_temp = storage_service.upload_path(
        upload.temp_file_path,
        subfolder=temp_video_prefix(rsrc_no=current_rsrc_no, upload_id=upload.upload_id),
        file_name=upload.original_file_name,
        content_type=upload.content_type,
    )
    Path(upload.temp_file_path).unlink(missing_ok=True)
    upload.stored_file_name = stored_temp.file_name
    upload.temp_file_path = stored_temp.key


def initialize_direct_s3_upload_storage(upload: UploadedVideos, current_rsrc_no: int) -> Optional[dict]:
    if not storage_service.is_s3:
        return None

    multipart = storage_service.create_multipart_upload(
        subfolder=temp_video_prefix(rsrc_no=current_rsrc_no, upload_id=upload.upload_id),
        file_name=upload.original_file_name,
        content_type=upload.content_type,
    )
    upload.upload_strategy = "s3_multipart"
    upload.stored_file_name = multipart["file_name"]
    upload.temp_file_path = multipart["key"]
    upload.multipart_object_key = multipart["key"]
    upload.multipart_upload_id = multipart["multipart_upload_id"]
    return multipart


def build_direct_s3_part_upload_url(upload: UploadedVideos, part_number: int) -> str:
    if not upload.multipart_upload_id or not upload.multipart_object_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload session is not configured for direct S3 multipart upload",
        )

    return storage_service.generate_multipart_part_url(
        key=upload.multipart_object_key,
        multipart_upload_id=upload.multipart_upload_id,
        part_number=part_number,
    )


def complete_direct_s3_upload_storage(upload: UploadedVideos, parts: list[dict]) -> None:
    if not upload.multipart_upload_id or not upload.multipart_object_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload session is not configured for direct S3 multipart upload",
        )
    if not parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded S3 parts are required to complete multipart upload",
        )

    storage_service.complete_multipart_upload(
        key=upload.multipart_object_key,
        multipart_upload_id=upload.multipart_upload_id,
        parts=[
            {"PartNumber": part["part_number"], "ETag": part["etag"]}
            for part in parts
        ],
    )
    upload.temp_file_path = upload.multipart_object_key
    upload.multipart_upload_id = None
    upload.multipart_object_key = None


def abort_direct_s3_upload_storage(upload: UploadedVideos) -> bool:
    aborted = storage_service.abort_multipart_upload(
        key=upload.multipart_object_key,
        multipart_upload_id=upload.multipart_upload_id,
    )
    upload.multipart_upload_id = None
    upload.multipart_object_key = None
    return aborted


def prepare_upload_file_for_metadata(upload: UploadedVideos) -> tuple[Path, Optional[Path]]:
    if not upload.temp_file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uploaded temp file is no longer available. The upload may have been cancelled.",
        )

    if storage_service.is_s3:
        local_path = Path("/tmp") / f"metadata_{upload.upload_id}{upload.file_ext}"
        storage_service.download_to_path(upload.temp_file_path, local_path)
        return local_path, local_path

    local_path = Path(upload.temp_file_path)
    if not local_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uploaded temp file is no longer available. The upload may have been cancelled.",
        )
    return local_path, None


def build_witness_video_download_url(
    video: WitnessVideos,
    *,
    request_base_url: Optional[str],
    current_rsrc_no: int,
    current_role: Optional[str],
):
    if storage_service.is_s3:
        if not storage_service.exists(video.file_path):
            return None, JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Video file is missing in storage",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return storage_service.generate_download_url(
            video.file_path,
            file_name=video.file_name or Path(video.file_path).name,
        ), None

    if str(video.file_path).startswith(("http://", "https://")):
        return video.file_path, None

    file_path = Path(video.file_path)
    if not file_path.exists():
        return None, JSONResponse(
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "Video file is missing on server",
                "success": False,
                "result": {},
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    base_url = (request_base_url or "").rstrip("/")
    download_token = create_video_download_token(video.id, current_rsrc_no, current_role)
    return f"{base_url}/witnesses/videos/{video.id}/download?token={download_token}", None


def build_witness_video_download_response(video: WitnessVideos):
    if storage_service.is_s3:
        if not storage_service.exists(video.file_path):
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Video file is missing in storage",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )
        download_url = storage_service.generate_download_url(
            video.file_path,
            file_name=video.file_name or Path(video.file_path).name,
        )
        return RedirectResponse(url=download_url, status_code=status.HTTP_302_FOUND)

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
        headers={"Content-Disposition": f"attachment; filename={download_name}"},
    )


def build_complete_video_download_url(
    witness: Witnesses,
    *,
    request_base_url: Optional[str],
    current_rsrc_no: int,
    current_role: Optional[str],
):
    file_name = witness.merged_video_name or Path(witness.merged_video_path).name
    if storage_service.is_s3:
        return storage_service.generate_download_url(
            witness.merged_video_path,
            file_name=file_name,
        )

    base_url = (request_base_url or "").rstrip("/")
    download_token = create_complete_video_download_token(witness.id, current_rsrc_no, current_role)
    return f"{base_url}/witnesses/{witness.id}/complete-video/download?token={download_token}"


def build_complete_video_download_response(witness: Witnesses):
    download_name = witness.merged_video_name or Path(witness.merged_video_path).name
    if storage_service.is_s3:
        download_url = storage_service.generate_download_url(
            witness.merged_video_path,
            file_name=download_name,
        )
        return RedirectResponse(url=download_url, status_code=status.HTTP_302_FOUND)

    file_path = Path(witness.merged_video_path)
    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename={download_name}"},
    )


def get_storage_backend_name() -> str:
    return storage_service.backend
