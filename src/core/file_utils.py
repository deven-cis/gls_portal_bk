import asyncio
import json
import time
import uuid
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import UploadFile, HTTPException, status
import aiofiles
from src.core.config import config
from src.core.logger import logger

ALLOWED_EXTENSIONS = {'.docx', '.pdf'}
ALLOWED_VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.mpeg', '.mpg', '.avi',
    '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'
}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
UPLOAD_BASE_DIR = Path("uploads")
TEMP_VIDEO_UPLOAD_DIR = UPLOAD_BASE_DIR / "_temp_videos"
UPLOAD_SESSION_DIR = UPLOAD_BASE_DIR / "_video_upload_sessions"
UPLOAD_SESSION_CHUNK_DIR = UPLOAD_SESSION_DIR / "chunks"
UPLOAD_SESSION_MANIFEST_DIR = UPLOAD_SESSION_DIR / "manifests"


def validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required"
        )
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only .docx and .pdf files are allowed. Got: {file_ext}"
        )


def validate_video_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required"
        )


def validate_video_filename(file_name: str) -> str:
    if not file_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required"
        )

    file_ext = Path(file_name).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only video files (.mp4, .avi, .mov, .mkv, .webm, .mpeg, .mpg, .wmv, .flv, .m4v, .3gp) "
                f"are allowed. Got: {file_ext}"
            )
        )
    return file_ext
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only video files (.mp4, .avi, .mov, .mkv, .webm) are allowed. Got: {file_ext}"
        )


def validate_image_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required"
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only image files (.jpg, .jpeg, .png, .gif, .webp) are allowed. Got: {file_ext}"
        )


async def save_file(file: UploadFile, subfolder: str) -> tuple[str, str]:
    validate_file(file)
    
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    upload_dir = UPLOAD_BASE_DIR / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / unique_filename
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    return file.filename, str(file_path)


async def extract_video_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract server-side metadata for uploaded video files.
    This replaces client-side metadata probing and keeps the source of truth in the backend.
    """
    probe_started_at = time.perf_counter()
    try:
        process = await asyncio.create_subprocess_exec(
            config.RESOLVED_FFPROBE_PATH,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        except asyncio.TimeoutError:
            process.kill()
            logger.warning(
                "ffprobe timeout for %s after %.2fs",
                file_path,
                time.perf_counter() - probe_started_at,
            )
            return {}

        if process.returncode != 0:
            stderr_text = stderr.decode(errors="ignore").strip()
            logger.warning(
                "ffprobe failed for %s after %.2fs: %s",
                file_path,
                time.perf_counter() - probe_started_at,
                stderr_text or "unknown error",
            )
            return {}

        info = json.loads(stdout or b"{}")
        fmt = info.get("format", {})
        streams = info.get("streams", [])

        timecode = None
        for stream in streams:
            tags = stream.get("tags", {}) or {}
            if tags.get("timecode"):
                timecode = tags["timecode"]
                break

        metadata = {
            "duration_seconds": float(fmt.get("duration", 0) or 0),
            "file_size": int(fmt.get("size", 0) or 0),
            "timecode": timecode,
            "format_name": fmt.get("format_name"),
        }

        logger.info(
            "Metadata extracted for %s in %.2fs: duration=%.2fs size=%s bytes timecode=%s format=%s",
            file_path,
            time.perf_counter() - probe_started_at,
            metadata["duration_seconds"],
            metadata["file_size"],
            metadata["timecode"],
            metadata["format_name"],
        )
        return metadata
    except FileNotFoundError:
        logger.warning(
            "ffprobe is not installed or not available at '%s' (checked for %.2fs)",
            config.RESOLVED_FFPROBE_PATH,
            time.perf_counter() - probe_started_at,
        )
        return {}
    except Exception as e:
        logger.warning(
            "ffprobe failed for %s after %.2fs: %s",
            file_path,
            time.perf_counter() - probe_started_at,
            str(e),
        )
        return {}


async def save_video_file(file: UploadFile, subfolder: str, chunk_number: Optional[int] = None, upload_id: Optional[str] = None) -> tuple[str, str, Dict[str, Any]]:
    """Save video using chunked streaming to avoid loading entire file in memory."""
    validate_video_file(file)
    save_started_at = time.perf_counter()
    
    file_ext = Path(file.filename).suffix.lower()
    upload_dir = UPLOAD_BASE_DIR / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    if upload_id:
        unique_filename = f"{upload_id}{file_ext}"
        file_path = upload_dir / unique_filename
        mode = "ab" if chunk_number is not None else "wb"
    else:
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / unique_filename
        mode = "wb"
    
    # Chunked streaming: 100MB chunks reduce I/O loop overhead for large uploads.
    chunk_size = 100 * 1024 * 1024
    total_size = 0
    chunk_count = 0
    try:
        async with aiofiles.open(file_path, mode) as buffer:
            while chunk := await file.read(chunk_size):
                await buffer.write(chunk)
                total_size += len(chunk)
                chunk_count += 1
        logger.info(
            "Video file saved: %s (%.2fMB) using %s mode in %.2fs across %s chunk(s)",
            unique_filename,
            total_size / (1024 * 1024),
            mode,
            time.perf_counter() - save_started_at,
            chunk_count,
        )
    except Exception as e:
        logger.error(f"Error saving video file {unique_filename}: {str(e)}", exc_info=True)
        if Path(file_path).exists():
            Path(file_path).unlink()
        raise

    metadata_started_at = time.perf_counter()
    metadata = await extract_video_metadata(str(file_path))
    if not metadata.get("file_size"):
        metadata["file_size"] = total_size
    logger.info(
        "Video processing summary for %s: save_time=%.2fs metadata_time=%.2fs total_time=%.2fs",
        unique_filename,
        metadata_started_at - save_started_at,
        time.perf_counter() - metadata_started_at,
        time.perf_counter() - save_started_at,
    )

    return file.filename, str(file_path), metadata


def _ensure_upload_session_dirs() -> None:
    UPLOAD_SESSION_CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_SESSION_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_VIDEO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_temp_video_upload_path(upload_id: str, file_ext: str) -> Path:
    _ensure_upload_session_dirs()
    return TEMP_VIDEO_UPLOAD_DIR / f"{upload_id}{file_ext}"


async def append_upload_chunk_to_file(
    file_path: Path,
    file: UploadFile,
    mode: str = "ab",
    chunk_size: int = 50 * 1024 * 1024,
) -> int:
    bytes_written = 0
    async with aiofiles.open(file_path, mode) as buffer:
        while chunk := await file.read(chunk_size):
            await buffer.write(chunk)
            bytes_written += len(chunk)
    return bytes_written


def promote_video_to_final_storage(
    source_path: str,
    file_ext: str,
    subfolder: str,
) -> tuple[str, str]:
    upload_dir = UPLOAD_BASE_DIR / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)

    final_file_name = f"{uuid.uuid4()}{file_ext}"
    final_file_path = upload_dir / final_file_name
    shutil.move(str(source_path), str(final_file_path))
    return final_file_name, str(final_file_path)


def _get_upload_manifest_path(upload_id: str) -> Path:
    return UPLOAD_SESSION_MANIFEST_DIR / f"{upload_id}.json"


def _get_upload_chunk_path(upload_id: str, file_ext: str) -> Path:
    return UPLOAD_SESSION_CHUNK_DIR / f"{upload_id}{file_ext}.part"


def _load_upload_manifest(upload_id: str) -> Dict[str, Any]:
    manifest_path = _get_upload_manifest_path(upload_id)
    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {upload_id} not found",
        )

    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to read upload manifest for %s: %s", upload_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload manifest is corrupted",
        ) from exc


def _save_upload_manifest(upload_id: str, manifest: Dict[str, Any]) -> None:
    manifest_path = _get_upload_manifest_path(upload_id)
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")


def init_video_upload_session(
    file_name: str,
    file_size: Optional[int] = None,
    content_type: Optional[str] = None,
    total_chunks: Optional[int] = None,
) -> Dict[str, Any]:
    _ensure_upload_session_dirs()
    file_ext = validate_video_filename(file_name)
    upload_id = str(uuid.uuid4())

    manifest = {
        "upload_id": upload_id,
        "original_file_name": file_name,
        "file_ext": file_ext,
        "content_type": content_type,
        "expected_file_size": file_size,
        "total_chunks": total_chunks,
        "received_chunks": 0,
        "bytes_received": 0,
        "status": "initialized",
    }
    _save_upload_manifest(upload_id, manifest)

    logger.info(
        "Initialized video upload session %s for %s (size=%s, total_chunks=%s)",
        upload_id,
        file_name,
        file_size,
        total_chunks,
    )
    return manifest


async def append_video_upload_chunk(
    upload_id: str,
    chunk_number: int,
    total_chunks: int,
    file: UploadFile,
    chunk_size: int = 50 * 1024 * 1024,
) -> Dict[str, Any]:
    validate_video_file(file)
    manifest = _load_upload_manifest(upload_id)
    file_ext = manifest["file_ext"]
    chunk_path = _get_upload_chunk_path(upload_id, file_ext)

    expected_chunk = int(manifest.get("received_chunks", 0))
    if chunk_number != expected_chunk:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Expected chunk_number {expected_chunk}, got {chunk_number}",
        )

    if manifest.get("total_chunks") is None:
        manifest["total_chunks"] = total_chunks
    elif int(manifest["total_chunks"]) != int(total_chunks):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_chunks does not match the initialized upload session",
        )

    if chunk_number == 0 and chunk_path.exists():
        chunk_path.unlink()

    bytes_written = 0
    started_at = time.perf_counter()
    async with aiofiles.open(chunk_path, "ab") as buffer:
        while chunk := await file.read(chunk_size):
            await buffer.write(chunk)
            bytes_written += len(chunk)

    manifest["received_chunks"] = expected_chunk + 1
    manifest["bytes_received"] = int(manifest.get("bytes_received", 0)) + bytes_written
    manifest["status"] = "uploading" if manifest["received_chunks"] < manifest["total_chunks"] else "uploaded"
    _save_upload_manifest(upload_id, manifest)

    logger.info(
        "Stored chunk %s/%s for upload %s in %.2fs (%s bytes)",
        chunk_number + 1,
        total_chunks,
        upload_id,
        time.perf_counter() - started_at,
        bytes_written,
    )

    return {
        "upload_id": upload_id,
        "chunk_number": chunk_number,
        "received_chunks": manifest["received_chunks"],
        "total_chunks": manifest["total_chunks"],
        "bytes_received": manifest["bytes_received"],
        "status": manifest["status"],
    }


async def complete_video_upload(upload_id: str, subfolder: str = "witness_videos") -> Dict[str, Any]:
    manifest = _load_upload_manifest(upload_id)
    total_chunks = manifest.get("total_chunks")
    received_chunks = manifest.get("received_chunks", 0)
    if total_chunks is None or received_chunks != total_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is incomplete ({received_chunks}/{total_chunks} chunks received)",
        )

    file_ext = manifest["file_ext"]
    chunk_path = _get_upload_chunk_path(upload_id, file_ext)
    if not chunk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded chunk file not found",
        )

    upload_dir = UPLOAD_BASE_DIR / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    final_file_name = f"{uuid.uuid4()}{file_ext}"
    final_file_path = upload_dir / final_file_name
    started_at = time.perf_counter()
    shutil.move(str(chunk_path), str(final_file_path))

    metadata = await extract_video_metadata(str(final_file_path))
    if not metadata.get("file_size"):
        metadata["file_size"] = final_file_path.stat().st_size

    manifest.update({
        "status": "completed",
        "file_name": manifest["original_file_name"],
        "file_path": str(final_file_path),
        "stored_file_name": final_file_name,
        "file_size": metadata.get("file_size"),
        "duration_seconds": metadata.get("duration_seconds"),
        "timecode": metadata.get("timecode"),
        "format_name": metadata.get("format_name"),
        "completed_in_seconds": round(time.perf_counter() - started_at, 2),
    })
    _save_upload_manifest(upload_id, manifest)

    logger.info(
        "Completed upload %s for %s in %.2fs",
        upload_id,
        final_file_name,
        time.perf_counter() - started_at,
    )
    return {
        "upload_id": upload_id,
        "file_name": manifest["file_name"],
        "file_path": manifest["file_path"],
        "file_size": manifest["file_size"],
        "duration_seconds": manifest["duration_seconds"],
        "timecode": manifest["timecode"],
        "format_name": manifest["format_name"],
        "status": manifest["status"],
    }


def get_completed_video_upload(upload_id: str) -> Dict[str, Any]:
    manifest = _load_upload_manifest(upload_id)
    if manifest.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload {upload_id} is not completed",
        )
    return manifest


async def save_image_file(file: UploadFile, subfolder: str) -> tuple[str, str]:
    validate_image_file(file)

    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    upload_dir = UPLOAD_BASE_DIR / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return file.filename, str(file_path)


async def save_multiple_files(files: List[UploadFile], subfolder: str) -> List[tuple[str, str]]:
    results = []
    for file in files:
        file_name, file_path = await save_file(file, subfolder)
        results.append((file_name, file_path))
    return results
