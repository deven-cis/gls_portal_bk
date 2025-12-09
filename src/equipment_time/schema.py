from typing import Optional
from datetime import time
from decimal import Decimal
from pydantic import BaseModel


class EquipmentTimeSchema(BaseModel):
    id: Optional[int] = None
    job_no: int
    laptop_used: Optional[bool] = False
    pip_used: Optional[bool] = False
    exhibit_tech: Optional[bool] = False
    parking_cost: Optional[Decimal] = Decimal('0.00')
    time_after: Optional[time] = None

    class Config:
        from_attributes = True


class EquipmentTimeCreateSchema(BaseModel):
    job_no: int
    laptop_used: Optional[bool] = False
    pip_used: Optional[bool] = False
    exhibit_tech: Optional[bool] = False
    parking_cost: Optional[Decimal] = Decimal('0.00')
    time_after: Optional[time] = None


class EquipmentTimeUpdateSchema(BaseModel):
    laptop_used: Optional[bool] = None
    pip_used: Optional[bool] = None
    exhibit_tech: Optional[bool] = None
    parking_cost: Optional[Decimal] = None
    time_after: Optional[time] = None

