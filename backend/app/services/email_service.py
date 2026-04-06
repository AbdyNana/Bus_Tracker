import os
from email.message import EmailMessage
import aiosmtplib
import logging

logger = logging.getLogger(__name__)

async def send_generated_email(to_email: str, subject: str, generated_body: str) -> bool:
    """
    Sends an email using SMTP configuration.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_user, smtp_password]):
        logger.error("SMTP Configuration is missing in environment variables.")
        return False

    message = EmailMessage()
    message["From"] = smtp_user
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(generated_body)

    try:
        await aiosmtplib.send(
            message,
            hostname=smtp_server,
            port=smtp_port,
            start_tls=True,
            username=smtp_user,
            password=smtp_password
        )
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
