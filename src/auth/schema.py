from pydantic import BaseModel


class LoginCredentialSchema(BaseModel):
    login_name: str
    login_password: str

class UserResponseSchema(BaseModel):
    id: int
    full_name: str
    email: str
    login_name: str
    require_password_change: bool = False  
    entered_by: int
    last_modified_by: int

class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    user: UserResponseSchema


class PasswordResetSchema(BaseModel):
    token: str
    new_password: str
 
 
class LogoutResponseSchema(BaseModel):
    message: str
    success: bool


class PasswordChangeSchema(BaseModel):
    user_id: int
    old_password: str
    new_password: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str