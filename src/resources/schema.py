from typing import Optional
from pydantic import BaseModel


class ResourceResponseSchema(BaseModel):
    rsrc_no: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    login_name: Optional[str] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True
        
        
        