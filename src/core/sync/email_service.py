import secrets
import string
from typing import Optional
from src.core.utils import send_email
from src.core.config import config
from src.core.logger import logger


def generate_temporary_password(length: int = 12) -> str:
    try:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    except Exception as e:
        logger.error(f"Error generating temporary password: {str(e)}")
        return None


def send_user_welcome_notification(
    email: str,
    first_name: str,
    login_name: str,
    temp_password: str,
    login_url: Optional[str] = None
) -> bool:

    try:
        login_url = login_url or config.FRONTEND_URL
        
        email_context = {
            'first_name': first_name or 'User',
            'username': login_name,
            'temp_password': temp_password,
            'login_url': login_url
        }
        
        send_email(
            receiver_email=email,
            subject="Welcome to Gallo Legal Services - Your Login Credentials",
            template_name="welcome_user.html",
            context=email_context
        )
        
        logger.info(f"Welcome email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {str(e)}", exc_info=True)
        return False

