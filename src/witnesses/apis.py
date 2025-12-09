from typing import List, Optional
from fastapi import Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from datetime import time
from pathlib import Path

from src.auth.utils import get_current_user
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.jobs.models import Jobs
from src.core.file_utils import save_video_file
from src.core.logger import logger


async def list_witnesses(
    job_no: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
) -> List[Witnesses]:
    try:
        db = Witnesses.get_session()
        query = db.query(Witnesses).filter(~Witnesses.is_archived)
        
        if job_no:
            query = query.filter(Witnesses.job_no == job_no)
        
        witnesses = query.all()
        logger.info(f"Successfully retrieved {len(witnesses)} witnesses")
        return witnesses
    except Exception as e:
        logger.error(f"Error listing witnesses: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_witness(
    witness_id: int,
    current_user: dict = Depends(get_current_user),
) -> Witnesses:
    try:
        db = Witnesses.get_session()
        witness = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            ~Witnesses.is_archived
        ).first()
        
        if not witness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Witness with ID {witness_id} not found"
            )
        return witness
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting witness {witness_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def create_witness(
    job_no: int = Form(...),
    witness_name: str = Form(...),
    witness_email: Optional[str] = Form(None),
    read_on_text: str = Form(...),
    read_on_time: str = Form(...),
    read_off_text: str = Form(...),
    read_off_time: str = Form(...),
    current_user: dict = Depends(get_current_user),
) -> Witnesses:
    try:
        db = Witnesses.get_session()
        job = db.query(Jobs).filter(Jobs.job_no == job_no).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with job_no {job_no} not found"
            )
        
        read_on_time_obj = time.fromisoformat(read_on_time) if isinstance(read_on_time, str) else read_on_time
        read_off_time_obj = time.fromisoformat(read_off_time) if isinstance(read_off_time, str) else read_off_time
        
        witness = Witnesses(
            job_no=job_no,
            witness_name=witness_name,
            witness_email=witness_email,
            read_on_text=read_on_text,
            read_on_time=read_on_time_obj,
            read_off_text=read_off_text,
            read_off_time=read_off_time_obj,
        )
        
        witness = Witnesses.save(witness)
        logger.info(f"Successfully created witness {witness.id} - {witness_name}")
        return witness
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating witness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def update_witness(
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
    current_user: dict = Depends(get_current_user),
) -> Witnesses:
    try:
        db = Witnesses.get_session()
        witness = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            ~Witnesses.is_archived
        ).first()
        
        if not witness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Witness with ID {witness_id} not found"
            )
        
        if witness_name is not None:
            witness.witness_name = witness_name
        if witness_email is not None:
            witness.witness_email = witness_email
        if actual_start_time is not None:
            witness.actual_start_time = time.fromisoformat(actual_start_time) if isinstance(actual_start_time, str) else actual_start_time
        if actual_end_time is not None:
            witness.actual_end_time = time.fromisoformat(actual_end_time) if isinstance(actual_end_time, str) else actual_end_time
        if read_on_text is not None:
            witness.read_on_text = read_on_text
        if read_on_time is not None:
            witness.read_on_time = time.fromisoformat(read_on_time) if isinstance(read_on_time, str) else read_on_time
        if read_off_text is not None:
            witness.read_off_text = read_off_text
        if read_off_time is not None:
            witness.read_off_time = time.fromisoformat(read_off_time) if isinstance(read_off_time, str) else read_off_time
        
        from src.core.context import get_context
        from datetime import datetime
        entered_by = get_context('entered_by') or 0
        witness.last_modified_at = datetime.now()
        witness.last_modified_by = entered_by
        
        db.commit()
        db.refresh(witness)
        logger.info(f"Successfully updated witness {witness_id}")
        return witness
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating witness {witness_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def delete_witness(
    witness_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    try:
        db = Witnesses.get_session()
        witness = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            ~Witnesses.is_archived
        ).first()
        
        if not witness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Witness with ID {witness_id} not found"
            )
        
        witness.is_archived = True
        from src.core.context import get_context
        from datetime import datetime
        entered_by = get_context('entered_by') or 0
        witness.last_modified_at = datetime.now()
        witness.last_modified_by = entered_by
        
        db.commit()
        logger.info(f"Successfully deleted witness {witness_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting witness {witness_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def add_witness_video(
    witness_id: int,
    job_no: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    video: UploadFile = File(...),
    chunk_number: Optional[int] = Form(None),
    upload_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
) -> WitnessVideos:
    try:
        db = Witnesses.get_session()
        witness = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            ~Witnesses.is_archived
        ).first()
        
        if not witness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Witness with ID {witness_id} not found"
            )
        
        job = db.query(Jobs).filter(Jobs.job_no == job_no).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with job_no {job_no} not found"
            )
        
        start_time_obj = time.fromisoformat(start_time) if isinstance(start_time, str) else start_time
        end_time_obj = time.fromisoformat(end_time) if isinstance(end_time, str) else end_time
        
        file_name, file_path = await save_video_file(video, "witness_videos", chunk_number, upload_id)
        
        if chunk_number is None or chunk_number == 0:
            witness_video = WitnessVideos(
                wit_no=witness_id,
                job_no=job_no,
                start_time=start_time_obj,
                end_time=end_time_obj,
                file_name=file_name,
                file_path=file_path,
            )
            witness_video = WitnessVideos.save(witness_video)
            logger.info(f"Successfully added video {witness_video.id} for witness {witness_id}")
            return witness_video
        else:
            existing_video = db.query(WitnessVideos).filter(
                WitnessVideos.file_path.like(f"%{upload_id}%"),
                ~WitnessVideos.is_archived
            ).first()
            if existing_video:
                logger.info(f"Successfully appended chunk {chunk_number} to video {existing_video.id}")
                return existing_video
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Upload ID not found for chunk upload"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding video for witness {witness_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def list_witness_videos(
    witness_id: Optional[int] = None,
    job_no: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
) -> List[WitnessVideos]:
    try:
        db = WitnessVideos.get_session()
        query = db.query(WitnessVideos).filter(WitnessVideos.is_archived == False)
        
        if witness_id:
            query = query.filter(WitnessVideos.wit_no == witness_id)
        if job_no:
            query = query.filter(WitnessVideos.job_no == job_no)
        
        videos = query.all()
        return videos
    except Exception as e:
        logger.error(f"Error listing witness videos: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def download_witness_video(
    video_id: int,
    current_user: dict = Depends(get_current_user),
) -> FileResponse:
    try:
        db = WitnessVideos.get_session()
        video = db.query(WitnessVideos).filter(
            WitnessVideos.id == video_id,
            ~WitnessVideos.is_archived
        ).first()
        
        if not video or not video.file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found"
            )
        
        file_path = Path(video.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video file not found on server"
            )
        
        return FileResponse(
            path=str(file_path),
            filename=video.file_name or f"video_{video_id}.mp4",
            media_type="video/mp4"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video {video_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def delete_witness_video(
    video_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    try:
        db = WitnessVideos.get_session()
        video = db.query(WitnessVideos).filter(
            WitnessVideos.id == video_id,
            ~WitnessVideos.is_archived
        ).first()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found"
            )
        
        video.is_archived = True
        from src.core.context import get_context
        from datetime import datetime
        entered_by = get_context('entered_by') or 0
        video.last_modified_at = datetime.now()
        video.last_modified_by = entered_by
        
        db.commit()
        logger.info(f"Successfully deleted witness video {video_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting video {video_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

