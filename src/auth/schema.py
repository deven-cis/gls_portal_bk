from pydantic import BaseModel


class LoginCredentialSchema(BaseModel):
    """
    Login Credential Schema
    """
    login_name: str
    login_password: str

class TokenResponseSchema(BaseModel):
    """
    Token Response Schema
    """
    access_token: str
    refresh_token: str


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