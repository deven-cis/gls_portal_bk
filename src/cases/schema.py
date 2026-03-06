from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CaseSchema(BaseModel):
    id: int
    case_no: Optional[int] = None
    case_short_name: Optional[str] = None
    case_full_name: Optional[str] = None
    case_type: Optional[str] = None
    status: Optional[str] = None
    case_number: Optional[str] = None
    trial_date: Optional[datetime] = None
    entered_at: Optional[datetime] = None
    last_modified_at: Optional[datetime] = None
    entered_by: Optional[int] = None
    last_modified_by: Optional[int] = None

    class Config:
        from_attributes = True


class CaseListSchema(BaseModel):
    id: int
    case_no: Optional[int] = None
    case_short_name: Optional[str] = None
    case_full_name: Optional[str] = None
    case_type: Optional[str] = None
    case_number: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True

class CaseEditSchema(BaseModel):
    case_short_name: Optional[str] = None
    case_number: Optional[str] = None

    class Config:
        from_attributes = True 

class GetCaseSchema(BaseModel):
    case_short_name: Optional[str] = None
    case_number: Optional[str] = None
    mark_is_done: Optional[bool] = None

    class Config:
        from_attributes = True 


class MarkCaseAsDoneSchema(BaseModel):
    is_done: bool = True

    class Config:
        from_attributes = True

        