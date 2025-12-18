from typing import Optional
from datetime import time
from pydantic import BaseModel

class WitnessVideoSchema(BaseModel):
    id: Optional[int] = None
    wit_no: int
    job_no: int
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None

    class Config:
        from_attributes = True