from typing import Optional
from pydantic import BaseModel


class AdditionalDocumentSchema(BaseModel):
    id: Optional[int] = None
    job_no: int
    billing_id: Optional[int] = None
    equipment_time_id: Optional[int] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None

    class Config:
        from_attributes = True


class AdditionalDocumentCreateSchema(BaseModel):
    job_no: int
    billing_id: Optional[int] = None
    equipment_time_id: Optional[int] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None


class AdditionalDocumentUpdateSchema(BaseModel):
    billing_id: Optional[int] = None
    equipment_time_id: Optional[int] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None

