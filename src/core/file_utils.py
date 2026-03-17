import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
import aiofiles
from src.core.logger import logger

ALLOWED_EXTENSIONS = {'.docx', '.pdf'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
UPLOAD_BASE_DIR = Path("uploads")


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


async def save_video_file(file: UploadFile, subfolder: str, chunk_number: Optional[int] = None, upload_id: Optional[str] = None) -> tuple[str, str]:
    """Save video using chunked streaming to avoid loading entire file in memory."""
    validate_video_file(file)
    
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
    
    # Chunked streaming: write in 1MB chunks instead of loading entire file
    chunk_size = 1024 * 1024  # 1MB chunks
    total_size = 0
    try:
        async with aiofiles.open(file_path, mode) as buffer:
            while chunk := await file.read(chunk_size):
                await buffer.write(chunk)
                total_size += len(chunk)
        logger.info(f"Video file saved: {unique_filename} ({total_size / (1024*1024):.2f}MB) using {mode} mode")
    except Exception as e:
        logger.error(f"Error saving video file {unique_filename}: {str(e)}", exc_info=True)
        if Path(file_path).exists():
            Path(file_path).unlink()
        raise
    
    return file.filename, str(file_path)


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
