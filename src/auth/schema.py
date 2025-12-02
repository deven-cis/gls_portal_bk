from pydantic import BaseModel, EmailStr


class LoginCredentialSchema(BaseModel):
    """
    Login Credential Schema
    """
    login_name: EmailStr
    login_password: str

class TokenResponseSchema(BaseModel):
    """
    Token Response Schema
    """
    access_token: str
    refresh_token: str
