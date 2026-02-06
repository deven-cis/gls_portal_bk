from typing import Optional, List
from pydantic import BaseModel


class BillingSchema(BaseModel):
    id: Optional[int] = None
    job_no: int
    cancel_en_route: Optional[bool] = False
    cancel_setup: Optional[bool] = False
    billing_notes: Optional[str] = None
    videographer_hours_present: Optional[str] = None
    file_hours_length: Optional[str] = None
    camera_captured_file_name: Optional[str] = None
    camera_captured_file_path: Optional[str] = None

    class Config:
        from_attributes = True


class AdditionalDocumentResponseSchema(BaseModel):
    id: int
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    job_no: int
    billing_id: Optional[int] = None

    class Config:
        from_attributes = True


class BillingWithDocumentsSchema(BaseModel):
    id: Optional[int] = None
    job_no: int
    cancel_en_route: Optional[bool] = False
    cancel_setup: Optional[bool] = False
    billing_notes: Optional[str] = None
    videographer_hours_present: Optional[str] = None
    file_hours_length: Optional[str] = None
    camera_captured_file_name: Optional[str] = None
    camera_captured_file_path: Optional[str] = None
    documents: List[AdditionalDocumentResponseSchema] = []

    class Config:
        from_attributes = True


class BillingCreateSchema(BaseModel):
    job_no: int
    cancel_en_route: Optional[bool] = False
    cancel_setup: Optional[bool] = False
    billing_notes: Optional[str] = None
    videographer_hours_present: Optional[str] = None
    file_hours_length: Optional[str] = None


class BillingUpdateSchema(BaseModel):
    cancel_en_route: Optional[bool] = None
    cancel_setup: Optional[bool] = None
    billing_notes: Optional[str] = None
    videographer_hours_present: Optional[str] = None
    file_hours_length: Optional[str] = None

