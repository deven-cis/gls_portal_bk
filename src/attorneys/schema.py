from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class AttorneySchema(BaseModel):
    id: int
    job_no: int
    attorney_name: str
    firm_name: str
    notes: str
    order_details: str
    file_name: Optional[str] = None
    file_name_path: Optional[str] = None
    camera_captured_file_name: Optional[str] = None
    camera_captured_file_path: Optional[str] = None
    entered_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes = True,
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class AttorneyCreateSchema(BaseModel):
    job_no: int
    attorney_name: str
    firm_name: str
    notes: str
    order_details: str
    file_name: Optional[str] = None
    file_name_path: Optional[str] = None


class AttorneyUpdateSchema(BaseModel):
    id: int
    attorney_name: Optional[str] = None
    firm_name: Optional[str] = None
    notes: Optional[str] = None
    order_details: Optional[str] = None
    file_name: Optional[str] = None
    file_name_path: Optional[str] = None

