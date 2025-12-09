from typing import Optional
from datetime import time
from pydantic import BaseModel


class BillingSchema(BaseModel):
    id: Optional[int] = None
    job_no: int
    cancel_en_route: Optional[bool] = False
    cancel_setup: Optional[bool] = False
    billing_notes: Optional[str] = None
    videographer_hours_present: Optional[time] = None
    file_hours_length: Optional[time] = None

    class Config:
        from_attributes = True


class BillingCreateSchema(BaseModel):
    job_no: int
    cancel_en_route: Optional[bool] = False
    cancel_setup: Optional[bool] = False
    billing_notes: Optional[str] = None
    videographer_hours_present: Optional[time] = None
    file_hours_length: Optional[time] = None


class BillingUpdateSchema(BaseModel):
    cancel_en_route: Optional[bool] = None
    cancel_setup: Optional[bool] = None
    billing_notes: Optional[str] = None
    videographer_hours_present: Optional[time] = None
    file_hours_length: Optional[time] = None

