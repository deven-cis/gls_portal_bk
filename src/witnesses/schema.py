from typing import Optional, List
from datetime import time, datetime
from pydantic import BaseModel


class WitnessVideoSchema(BaseModel):
    id: Optional[int] = None
    wit_no: int
    job_no: int
    start_time: time
    end_time: time
    file_name: Optional[str] = None
    file_path: Optional[str] = None

    class Config:
        from_attributes = True


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
    read_on_time: time
    read_off_text: str
    read_off_time: time
    witness_videos: Optional[List[WitnessVideoSchema]] = []

    class Config:
        from_attributes = True


class WitnessCreateSchema(BaseModel):
    job_no: int
    witness_name: str
    witness_email: Optional[str] = None
    read_on_text: str
    read_on_time: time
    read_off_text: str
    read_off_time: time


class WitnessUpdateSchema(BaseModel):
    witness_name: Optional[str] = None
    witness_email: Optional[str] = None
    actual_start_time: Optional[time] = None
    actual_end_time: Optional[time] = None
    read_sign_date: Optional[datetime] = None
    read_sign_to: Optional[int] = None
    read_on_text: Optional[str] = None
    read_on_time: Optional[time] = None
    read_off_text: Optional[str] = None
    read_off_time: Optional[time] = None

