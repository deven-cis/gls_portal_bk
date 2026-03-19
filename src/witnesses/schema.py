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
    actual_start_time: Optional[str] = None 
    actual_end_time: Optional[str] = None 
    read_sign_date: Optional[str] = None 
    read_sign_to: Optional[int] = None
    read_on_text: Optional[str] = None
    read_on_time: Optional[str] = None 
    read_off_text: Optional[str] = None
    read_off_time: Optional[str] = None 

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
    id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    file_index: Optional[int] = None
    upload_token: Optional[str] = None
    delete: bool = False


class WitnessSaveAllPayloadSchema(BaseModel):
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

    replace_videos: bool = False

    videos: List[WitnessVideoUpsertSchema] = Field(default_factory=list)



class WitnessCompletedDetailsSchema(BaseModel):
    witness_name:Optional[str] = None
    videos: List[WitnessVideoUpsertSchema] = Field(default_factory=list)


class WitnessVideoUploadInitSchema(BaseModel):
    file_name: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    total_chunks: Optional[int] = None


class WitnessVideoUploadCompleteSchema(BaseModel):
    upload_id: str


class WitnessVideoUploadCancelSchema(BaseModel):
    upload_id: str
