from typing import Optional, List
from datetime import time
from decimal import Decimal
from pydantic import BaseModel


class EquipmentTimeSchema(BaseModel):
    id: Optional[int] = None
    job_no: int
    laptop_used: Optional[bool] = False
    pip_used: Optional[bool] = False
    exhibit_tech: Optional[bool] = False
    parking_cost: Optional[str] = "0.00"  # Changed to str for JSON serialization
    time_after: Optional[str] = None  # Changed to str for form data compatibility

    class Config:
        from_attributes = True


class AdditionalDocumentResponseSchema(BaseModel):
    """Schema for additional document in equipment_time response"""
    id: int
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    job_no: int
    equipment_time_id: Optional[int] = None

    class Config:
        from_attributes = True


class EquipmentTimeWithDocumentsSchema(BaseModel):
    """Complete equipment_time response with associated documents"""
    id: Optional[int] = None
    job_no: int
    laptop_used: Optional[bool] = False
    pip_used: Optional[bool] = False
    exhibit_tech: Optional[bool] = False
    parking_cost: Optional[str] = "0.00"  # Changed to str for JSON serialization
    time_after: Optional[str] = None
    documents: List[AdditionalDocumentResponseSchema] = []

    class Config:
        from_attributes = True


class EquipmentTimeCreateSchema(BaseModel):
    job_no: int
    laptop_used: Optional[bool] = False
    pip_used: Optional[bool] = False
    exhibit_tech: Optional[bool] = False
    parking_cost: Optional[Decimal] = Decimal('0.00')
    time_after: Optional[str] = None


class EquipmentTimeUpdateSchema(BaseModel):
    laptop_used: Optional[bool] = None
    pip_used: Optional[bool] = None
    exhibit_tech: Optional[bool] = None
    parking_cost: Optional[Decimal] = None
    time_after: Optional[str] = None

