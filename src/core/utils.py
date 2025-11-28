from typing import Optional, List, Dict, Any, Type

from fastapi.openapi.models import Link

from src.core.schema import ErrorResponse


DEFAULT_SCHEMA = {
    400: {
        "description": "Bad Request",
        "model": ErrorResponse,
        "content": {"application/json": {"example": {"detail": "Invalid input"}}}
    },
    401: {
        "description": "Unauthorized",
        "model": ErrorResponse,
        "content": {"application/json": {"example": {"detail": "Not authenticated"}}}
    },
    403: {
        "description": "Forbidden",
        "model": ErrorResponse,
        "content": {"application/json": {"example": {"detail": "Permission denied"}}}
    },
    404: {
        "description": "Not Found",
        "model": ErrorResponse,
        "content": {"application/json": {"example": {"detail": "Item not found"}}}
    },
    500: {
        "description": "Internal Server Error",
        "content": {"application/json": {"example": {"detail": "Unexpected server error"}}}
    },
    409: {
        "description": "Record already exist",
        "model": ErrorResponse,
        "content": {"application/json": {"example": {"detail": "Record already exist"}}}
    }   
}


def get_response_schema(
        response_schema: Optional[Type] = None,
        success_code: int = 200,
        include: Optional[List[int]] = None,
        links: Optional[Dict[str, Link]] = None
    ):
    responses = {}

    if response_schema:
        responses[success_code] = {
            "description": "Success Response",
            "model": response_schema
        }

    elif links:
        responses[success_code] = {
            "description": "Success Response",
            "links": links
        }

    if not include:
        responses = responses.update(DEFAULT_SCHEMA)
    else:
        for code, schema in DEFAULT_SCHEMA.items():
            if code in include:
                responses[code] = schema