from typing import Optional
from pydantic import BaseModel


class ResourceResponseSchema(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    login_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    entered_by: Optional[int] = None
    last_modified_by: Optional[int] = None

    class Config:
        from_attributes = True
        
        
        