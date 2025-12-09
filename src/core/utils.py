from typing import Optional, List, Dict, Any, Type
from fastapi.openapi.models import Link
from src.core.schema import ErrorResponse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
 
from src.core.config import config
from src.core.logger import logger

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

def send_email(receiver_email, subject, template_name, context):
    msg = MIMEMultipart()
    msg["From"] = config.SMTP_EMAIL
    msg["To"] = receiver_email
    msg["Subject"] = subject
 
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    message = template.render(email_data=context)
    print(message)
    msg.attach(MIMEText(message, "html"))
 
    try:
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_EMAIL, receiver_email, msg.as_string())
        server.quit()
 
    except Exception as e:
        logger.error(f"Failed to send email to {receiver_email}: {str(e)}")