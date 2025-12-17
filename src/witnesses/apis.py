from typing import List, Optional, Union
from fastapi import Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from datetime import time
from pathlib import Path
from sqlalchemy.orm import Session

from src.auth.utils import get_current_user
from src.witnesses.models import Witnesses
from src.cases.models import Cases
from src.witness_videos.models import WitnessVideos
from src.jobs.models import Jobs
from src.core.file_utils import save_video_file
from src.core.logger import logger
from src.core.context import get_context
from src.core.database import get_db
from sqlalchemy.orm import Session
from src.witnesses.schema import CreateWitnessFrontSchema, WitnessUpdateSchema
from datetime import datetime

async def list_witnesses(
    job_no: Optional[int] = None,
    current_user: dict = None,
    db: Session = Depends(get_db)
) -> List[Witnesses]:
    try:
        # Get user info from context first, fallback to current_user
        user_entered_by = get_context('entered_by')
        if not user_entered_by and current_user:
            user_entered_by = current_user.get('entered_by')
            
        logger.info(f"Listing witnesses for job {job_no}, entered_by: {user_entered_by}")
        
        query = db.query(Witnesses).filter(~Witnesses.is_archived)
        
        if job_no is not None:
            query = query.filter(Witnesses.job_no == job_no)
            
        if user_entered_by:
            query = query.filter(Witnesses.entered_by == user_entered_by)
        
        witnesses = query.all()
        logger.info(f"Successfully retrieved {len(witnesses)} witnesses" + 
                  (f" for job {job_no}" if job_no is not None else ""))
        return witnesses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing witnesses: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )


async def get_job_witnesses(
    job_no: int,
    current_user: dict = None,
    db: Session = Depends(get_db)
) -> List[Witnesses]:
    try:
        # Get user info from context first, fallback to current_user
        # user_entered_by = get_context('entered_by')
        # if not user_entered_by and current_user:
        #     user_entered_by = current_user.get('entered_by')
            
        # if not user_entered_by:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="User information not found"
        #     )
            
        logger.info(f"Getting witnesses for job {job_no}")
        
        witnesses = db.query(Witnesses).filter(
            Witnesses.job_no == job_no,
            ~Witnesses.is_archived
            # Witnesses.entered_by == user_entered_by,
        ).all()
        
        logger.info(f"Successfully retrieved {len(witnesses)} witnesses for job {job_no}")
        return witnesses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting witnesses for job {job_no}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def get_witness(
    witness_id: int,
    current_user: dict = None,
    db: Session = Depends(get_db)
) -> Witnesses:
    try:
        user_entered_by = get_context('entered_by')
        logger.info(f"Getting witness {witness_id} entered by {user_entered_by}")
        witness = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            Witnesses.entered_by == user_entered_by,
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


async def create_witness_name(
    data: CreateWitnessFrontSchema,
    db: Session = Depends(get_db)
) -> Witnesses:
    try:
        user_entered_by = get_context('entered_by')
        logger.info(f"Creating witness name payload: {data}")

        job = db.query(Jobs).filter(Jobs.job_no == data.job_no).first()
        if not job:
            raise HTTPException(    
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with job_no {job_no} not found"
            )

        case_info = db.query(Cases).filter(Cases.case_no == job.case_no).first()

        read_context = {
            "read_on_text": f"We are now on the record at [Time] on [Date]. This is the [Type] deposition of {data.witness_name} in the matter of {case_info.case_short_name} case number {case_info.case_number}",
            "read_off_text": f"We are now off the record at [Time]. This concludes the deposition of {data.witness_name}"
        }
        
        witness = Witnesses(
            job_no=data.job_no,
            witness_name=data.witness_name,
            read_on_text=read_context['read_on_text'],
            read_off_text=read_context['read_off_text'],
        )
        
        witness.save()
        
        return witness    

    except Exception as e:
        logger.error(f"Error creating witness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def create_witness(
    job_no: int = Form(...),
    witness_name: str = Form(...),
    witness_email: Optional[str] = Form(None),
    read_on_text: str = Form(...),
    read_on_time: str = Form(...),
    read_off_text: str = Form(...),
    read_off_time: str = Form(...),
    current_user: dict = None,
    db: Session = Depends(get_db)
) -> Witnesses:
    try:
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


def _parse_time_internal(value: str) -> Optional[time]:
    """
    Internal time parsing function.
    Returns None if value is invalid or empty.
    """
    # Handle None or non-string values
    if value is None:
        return None
    
    if not isinstance(value, str):
        try:
            value = str(value)
        except:
            return None
    
    # Strip whitespace
    value = value.strip()
    
    # Return None for empty strings
    if not value:
        return None
    
    # Early check for common invalid placeholders (case-insensitive)
    # This catches "string", "null", etc. before any processing
    invalid_values = ['string', 'null', 'none', '--:--', 'undefined', 'nan', 'none', 'null', '']
    value_lower = value.lower()
    if value_lower in invalid_values:
        return None
    
    # Additional check: if it contains only letters (no digits), it's invalid
    # Valid formats: HH:MM:SS, HH:MM, or just numbers
    if not any(c.isdigit() for c in value):
        return None
    
    # Additional safety: if it's a common word that's not a time, reject it
    if value_lower in ['string', 'time', 'date', 'datetime']:
        return None
    
    # Handle single digit hour (0-23)
    if value.isdigit() and len(value) <= 2:
        try:
            hour = int(value)
            if 0 <= hour <= 23:
                return time(hour, 0, 0)
        except:
            return None
        return None
    
    # Handle HH:MM format (add seconds if missing)
    if value.count(':') == 1:
        # Validate format before adding seconds
        parts = value.split(':')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            value += ':00'
        else:
            return None
    
    # Validate that it looks like a time format before parsing
    # Should be in format HH:MM:SS or HH:MM
    if ':' in value:
        parts = value.split(':')
        if len(parts) not in [2, 3]:
            return None
        # Check all parts are digits
        if not all(part.isdigit() for part in parts):
            return None
    
    # Try to parse ISO format - this is the only place that might raise ValueError
    try:
        return time.fromisoformat(value)
    except (ValueError, AttributeError, TypeError):
        return None


def parse_time(value: str) -> Optional[time]:
    """
    Parse time string to time object.
    Returns None if value is invalid or empty.
    NEVER raises exceptions - always returns None for invalid input.
    This is a safe wrapper that guarantees no exceptions.
    """
    try:
        return _parse_time_internal(value)
    except Exception as e:
        # Absolute safety net - catch ANY exception and return None
        logger.debug(f"Unexpected error in parse_time for value '{value}': {str(e)}")
        return None


async def update_witness(
    witness_id: int,
    update_data: WitnessUpdateSchema,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
) -> dict:
    try:
        # Get witness from database
        witness = db.query(Witnesses).filter(
            Witnesses.id == witness_id,
            ~Witnesses.is_archived
        ).first()
        
        if not witness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Witness not found"
            )
        
        # Track if any field was updated
        fields_updated = []
        
        # Get only fields that were provided (exclude unset, but include None and empty strings to handle clearing)
        update_dict = update_data.model_dump(exclude_unset=True)
        logger.info(f"Update dictionary: {update_dict}")
        # Update fields only if provided (not None)
        if "witness_name" in update_dict:
            witness_name = update_dict["witness_name"]
            if isinstance(witness_name, str) and witness_name.strip():
                witness.witness_name = witness_name.strip()
                fields_updated.append("witness_name")
            elif witness_name == "":
                witness.witness_name = ""
                fields_updated.append("witness_name")
        
        if "witness_email" in update_dict:
            witness_email = update_dict["witness_email"]
            witness.witness_email = witness_email.strip() if isinstance(witness_email, str) else witness_email
            fields_updated.append("witness_email")
        
        if "read_sign_date" in update_dict:
            witness.read_sign_date = update_dict["read_sign_date"]
            fields_updated.append("read_sign_date")
        
        if "read_sign_to" in update_dict:
            witness.read_sign_to = update_dict["read_sign_to"]
            fields_updated.append("read_sign_to")
        
        if "read_on_text" in update_dict:
            read_on_text = update_dict["read_on_text"]
            if isinstance(read_on_text, str) and read_on_text.strip():
                witness.read_on_text = read_on_text.strip()
                fields_updated.append("read_on_text")
            elif read_on_text == "":
                witness.read_on_text = ""
                fields_updated.append("read_on_text")
        
        if "read_off_text" in update_dict:
            read_off_text = update_dict["read_off_text"]
            if isinstance(read_off_text, str) and read_off_text.strip():
                witness.read_off_text = read_off_text.strip()
                fields_updated.append("read_off_text")
            elif read_off_text == "":
                witness.read_off_text = ""
                fields_updated.append("read_off_text")
        
        # Update time fields - only update if valid value provided, otherwise preserve existing
        if "actual_start_time" in update_dict:
            actual_start_time = update_dict["actual_start_time"]
            try:
                parsed_time = parse_time(actual_start_time) if actual_start_time else None
                # Only update if we got a valid parsed time, or if explicitly set to None/empty
                if parsed_time is not None:
                    witness.actual_start_time = parsed_time
                    fields_updated.append("actual_start_time")
                elif actual_start_time == "" or actual_start_time is None:
                    # Explicitly clearing the field
                    witness.actual_start_time = None
                    fields_updated.append("actual_start_time")
                # If parse_time returned None due to invalid format, skip update (preserve existing)
            except Exception as e:
                logger.warning(f"Error parsing actual_start_time '{actual_start_time}': {str(e)}. Preserving existing value.")
                # Preserve existing value on any error
        
        if "actual_end_time" in update_dict:
            actual_end_time = update_dict["actual_end_time"]
            try:
                parsed_time = parse_time(actual_end_time) if actual_end_time else None
                if parsed_time is not None:
                    witness.actual_end_time = parsed_time
                    fields_updated.append("actual_end_time")
                elif actual_end_time == "" or actual_end_time is None:
                    witness.actual_end_time = None
                    fields_updated.append("actual_end_time")
            except Exception as e:
                logger.warning(f"Error parsing actual_end_time '{actual_end_time}': {str(e)}. Preserving existing value.")
        
        if "read_on_time" in update_dict:
            read_on_time = update_dict["read_on_time"]
            try:
                parsed_time = parse_time(read_on_time) if read_on_time else None
                if parsed_time is not None:
                    witness.read_on_time = parsed_time
                    fields_updated.append("read_on_time")
                elif read_on_time == "" or read_on_time is None:
                    # For required fields, set default if explicitly cleared
                    witness.read_on_time = time(0, 0, 0)
                    fields_updated.append("read_on_time")
                # If invalid format, preserve existing value
            except Exception as e:
                logger.warning(f"Error parsing read_on_time '{read_on_time}': {str(e)}. Preserving existing value.")
        
        if "read_off_time" in update_dict:
            read_off_time = update_dict["read_off_time"]
            try:
                parsed_time = parse_time(read_off_time) if read_off_time else None
                if parsed_time is not None:
                    witness.read_off_time = parsed_time
                    fields_updated.append("read_off_time")
                elif read_off_time == "" or read_off_time is None:
                    # For required fields, set default if explicitly cleared
                    witness.read_off_time = time(0, 0, 0)
                    fields_updated.append("read_off_time")
                # If invalid format, preserve existing value
            except Exception as e:
                logger.warning(f"Error parsing read_off_time '{read_off_time}': {str(e)}. Preserving existing value.")
        
        # Save (handles last_modified_at and last_modified_by, commit and refresh)
        witness.save()
        
        # Prepare response message
        if fields_updated:
            message = f"Witness updated successfully. Fields updated: {', '.join(fields_updated)}"
        else:
            message = "No changes provided. Witness data remains unchanged."
        
        logger.info(f"Updated witness {witness_id}. Fields updated: {fields_updated}")
        
        # Return structured response
        return {
            "status_code": status.HTTP_200_OK,
            "result": witness,
            "message": message
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        # This should rarely happen now since parse_time handles errors gracefully
        # But keep it for other potential ValueError cases
        error_msg = str(e)
        if "isoformat" in error_msg.lower() or "time" in error_msg.lower():
            logger.warning(f"Time parsing error (should be handled by parse_time): {error_msg}")
            # Don't raise error, just log and return unchanged data
            return {
                "status_code": status.HTTP_200_OK,
                "result": witness,
                "message": "Update completed. Some invalid time values were ignored and existing values preserved."
            }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error updating witness {witness_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update witness"
        )



async def delete_witness(
    witness_id: int,
) -> None:
    try:
        witness = Witnesses.get_queryset().get(
            id=witness_id,
            is_archived=False
        )
        
        if not witness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Witness with ID {witness_id} not found"
            )
        
        witness.is_archived = True  
        witness.save()
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
    db: Session = Depends(get_db)
) -> WitnessVideos:
    try:
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

