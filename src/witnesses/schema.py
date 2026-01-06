from typing import Optional, List
from datetime import time, datetime
from pydantic import BaseModel, Field
from src.witness_videos.schema import WitnessVideoSchema


class WitnessVideoCreateSchema(BaseModel):
    wit_no: int
    job_no: int
    start_time: time
    end_time: time


class WitnessSchema(BaseModel):
    id: Optional[int] = None
    job_no: int
    witness_name: str
    witness_email: Optional[str] = None
    actual_start_time: Optional[time] = None
    actual_end_time: Optional[time] = None
    read_sign_date: Optional[datetime] = None
    read_sign_to: Optional[int] = None
    wit_no: Optional[int] = None
    read_on_text: str
    read_on_time: Optional[time] = None
    read_off_text: str
    read_off_time: Optional[time] = None
    # Model relationship is `Witnesses.witness_vid` but API field is `witness_videos`
    witness_videos: List[WitnessVideoSchema] = Field(
        default_factory=list,
        validation_alias="witness_vid",
        serialization_alias="witness_videos",
    )

    class Config:
        from_attributes = True


class WitnessNameSchema(BaseModel):
    job_no: int
    witness_name: str


class WitnessNameUpdateSchema(BaseModel):
    witness_name: str

class WitnessCreateSchema(BaseModel):
    id:int
    witness_name: str
    read_on_text: str
    read_on_time: Optional[time] = None
    read_off_text: str
    read_off_time: Optional[time] = None

    class Config:
        from_attributes = True

class CreateWitnessFrontSchema(BaseModel):
    job_no: int
    witness_name: str

    class Config:
        from_attributes = True

class WitnessUpdateSchema(BaseModel):
    job_no: Optional[int] = None
    witness_name: Optional[str] = None
    witness_email: Optional[str] = None
    actual_start_time: Optional[str] = None  # String from Form, will be parsed
    actual_end_time: Optional[str] = None  # String from Form, will be parsed
    read_sign_date: Optional[str] = None  # String from Form
    read_sign_to: Optional[int] = None
    read_on_text: Optional[str] = None
    read_on_time: Optional[str] = None  # String from Form, will be parsed
    read_off_text: Optional[str] = None
    read_off_time: Optional[str] = None  # String from Form, will be parsed

    class Config:
        from_attributes = True


class GetJobWitnessSchema(BaseModel):
    id: int
    job_no: int
    witness_name: str
    wit_no: Optional[int] = None
    read_on_text: str
    read_on_time: Optional[time] = None
    read_off_text: str
    read_off_time: Optional[time] = None
    witness_videos: List[WitnessVideoSchema] = Field(
        default_factory=list,
        validation_alias="witness_vid",
        serialization_alias="witness_videos",
    )
    
    class Config:
        from_attributes = True


class WitnessUpdateResponseSchema(BaseModel):
    status_code: int
    result: WitnessSchema
    message: str
    
    class Config:
        from_attributes = True


class WitnessVideoUpsertSchema(BaseModel):
    """
    Used by the save-all endpoint to upsert videos.
    - If `id` is provided: update that video row (or delete if delete=true)
    - If `id` is not provided: create a new video row
    - `file_index` points to the Nth uploaded file in the request's `files[]`
    """
    id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    file_index: Optional[int] = None
    delete: bool = False


class WitnessSaveAllPayloadSchema(BaseModel):
    """
    Payload for POST /witnesses/save-all.
    Send as JSON string in multipart field `payload`.
    """
    witness_id: Optional[int] = None
    job_no: int
    witness_name: Optional[str] = None
    witness_email: Optional[str] = None

    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None

    read_on_text: Optional[str] = None
    read_on_time: Optional[str] = None
    read_off_text: Optional[str] = None
    read_off_time: Optional[str] = None

    # If true, backend will archive any existing videos not included in `videos` list.
    # This supports "delete old video and add new video" or "delete all videos" when UI sends empty list.
    replace_videos: bool = False

    videos: List[WitnessVideoUpsertSchema] = Field(default_factory=list)



class WitnessCompletedDetailsSchema(BaseModel):
    witness_name:Optional[str] = None
    videos: List[WitnessVideoUpsertSchema] = Field(default_factory=list)