from typing import Optional

from pydantic import BaseModel

class UserResponseSchema(BaseModel):
    id: int
    full_name: str
    email: str
    login_name: str
    profile_image_url: Optional[str] = None
    entered_by: int
    last_modified_by: int
    
    class Config:
        from_attributes = True