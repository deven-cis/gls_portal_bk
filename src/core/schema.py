from pydantic import BaseModel


class ErrorResponse(BaseModel):
    details: str