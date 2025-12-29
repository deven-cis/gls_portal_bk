from pydantic import BaseModel


class LoginCredentialSchema(BaseModel):
    """
    Login Credential Schema
    """
    login_name: str
    login_password: str

class UserResponseSchema(BaseModel):
    """
    User Response Schema
    """
    id: int
    full_name: str
    email: str
    login_name: str
    require_password_change: bool = False  
    entered_by: int
    last_modified_by: int

class TokenResponseSchema(BaseModel):
    """
    Token Response Schema
    """
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    user: UserResponseSchema


class PasswordResetSchema(BaseModel):
    """
    Password Reset Schema
    """
    token: str
    new_password: str
 
 
class LogoutResponseSchema(BaseModel):
    """
    Logout Response Schema
    """
    message: str
    success: bool


class PasswordChangeSchema(BaseModel):
    """
    Password Change Schema
    """
    user_id: int
    old_password: str
    new_password: str


class RefreshTokenSchema(BaseModel):
    """
    Refresh Token Schema
    """
    refresh_token: str