import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.models import Notification, NotificationChannel
import structlog

logger = structlog.get_logger()


class NotificationService:

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        event_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            event_type=event_type,
            reference_id=reference_id,
            channel=channel,
        )
        db.add(notification)
        await db.flush()
        return notification

    @staticmethod
    async def send_email(to_email: str, subject: str, html_body: str):
        if not settings.SMTP_USER:
            logger.warning("SMTP not configured, skipping email")
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html"))

            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=False,
                start_tls=True,
            ) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(msg)

            logger.info("Email sent", to=to_email, subject=subject)
        except Exception as e:
            logger.error("Email failed", to=to_email, error=str(e))

    @staticmethod
    async def send_welcome_email(email: str, name: str):
        html = f"""
        <html><body>
        <h2>Welcome to FleetFlow, {name}!</h2>
        <p>Your account has been created successfully.</p>
        <p>Start creating deliveries today.</p>
        <br>
        <p>The FleetFlow Team</p>
        </body></html>
        """
        await NotificationService.send_email(email, "Welcome to FleetFlow!", html)

    @staticmethod
    async def send_password_reset_email(email: str, name: str, token: str):
        reset_url = f"http://localhost:3000/reset-password?token={token}"
        html = f"""
        <html><body>
        <h2>Password Reset Request</h2>
        <p>Hi {name},</p>
        <p>Click the link below to reset your password. This link expires in 1 hour.</p>
        <a href="{reset_url}" style="background:#3B82F6;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;">
            Reset Password
        </a>
        <p>If you didn't request this, ignore this email.</p>
        </body></html>
        """
        await NotificationService.send_email(email, "Reset your FleetFlow password", html)

    @staticmethod
    async def send_delivery_update_email(email: str, name: str, status: str, delivery_id: str):
        status_messages = {
            "ASSIGNED": "Your driver has been assigned!",
            "PICKED_UP": "Your parcel has been picked up!",
            "DELIVERED": "Your parcel has been delivered!",
            "CANCELLED": "Your delivery has been cancelled.",
        }
        message = status_messages.get(status, f"Delivery status updated to {status}")
        html = f"""
        <html><body>
        <h2>Delivery Update</h2>
        <p>Hi {name},</p>
        <p>{message}</p>
        <p>Delivery ID: <strong>{delivery_id[:8].upper()}</strong></p>
        </body></html>
        """
        await NotificationService.send_email(email, f"FleetFlow: {message}", html)
