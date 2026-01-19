"""
Email utilities for Stage 2 sync.
Handles sending welcome emails to new users with temporary passwords.
"""

import secrets
import string
from typing import Optional

from src.core.utils import send_email
from src.core.config import config
from src.core.logger import logger


def generate_temporary_password(length: int = 12) -> str:
    """
    Generate a cryptographically secure temporary password.
    
    Args:
        length: Length of the password (default: 12)
    
    Returns:
        A secure random password string
    """
    # Use a mix of uppercase, lowercase, digits, and special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def send_user_welcome_notification(
    email: str,
    first_name: str,
    login_name: str,
    temp_password: str,
    login_url: Optional[str] = None
) -> bool:
    """
    Send welcome email notification to a new user with login credentials.
    
    Args:
        email: User's email address
        first_name: User's first name (for greeting)
        login_name: User's login username
        temp_password: Temporary password to send
        login_url: Login URL (defaults to FRONTEND_URL from config)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        login_url = login_url or config.FRONTEND_URL
        
        # Prepare email context
        email_context = {
            'first_name': first_name or 'User',
            'username': login_name,
            'temp_password': temp_password,
            'login_url': login_url
        }
        
        # Send email
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

