"""
Email Service for User Notifications
Production-ready email service with multiple provider support
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json
from datetime import datetime

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class EmailMessage:
    """Email message structure"""
    to: str
    subject: str
    html_body: str
    text_body: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None

class EmailService:
    """
    Production-ready email service with multiple provider support
    
    Supports:
    - SMTP (generic)
    - SendGrid
    - AWS SES
    - Resend
    - Postmark
    """
    
    def __init__(self):
        """Initialize email service based on configuration"""
        self.provider = getattr(settings, 'email_provider', 'smtp')
        self.from_email = getattr(settings, 'from_email', 'noreply@yourdomain.com')
        
        # Provider-specific configuration
        if self.provider == 'smtp':
            self.smtp_host = getattr(settings, 'smtp_host', 'localhost')
            self.smtp_port = getattr(settings, 'smtp_port', 587)
            self.smtp_username = getattr(settings, 'smtp_username', None)
            self.smtp_password = getattr(settings, 'smtp_password', None)
            self.smtp_use_tls = getattr(settings, 'smtp_use_tls', True)
        
        elif self.provider == 'sendgrid':
            self.api_key = getattr(settings, 'sendgrid_api_key', None)
            
        elif self.provider == 'ses':
            self.aws_region = getattr(settings, 'aws_region', 'us-east-1')
            self.aws_access_key = getattr(settings, 'aws_access_key_id', None)
            self.aws_secret_key = getattr(settings, 'aws_secret_access_key', None)
            
        elif self.provider == 'resend':
            self.api_key = getattr(settings, 'resend_api_key', None)
            
        logger.info(f"Email service initialized with provider: {self.provider}")
    
    async def send_email(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Send email using configured provider
        
        Args:
            message: EmailMessage object with email details
            
        Returns:
            Dict with status and details
        """
        try:
            if not self._is_configured():
                logger.warning("Email service not properly configured")
                return {
                    "status": "error",
                    "message": "Email service not configured. Check environment variables.",
                    "provider": self.provider
                }
            
            # Set default from email if not provided
            if not message.from_email:
                message.from_email = self.from_email
            
            # Route to appropriate provider
            if self.provider == 'smtp':
                return await self._send_via_smtp(message)
            elif self.provider == 'sendgrid':
                return await self._send_via_sendgrid(message)
            elif self.provider == 'ses':
                return await self._send_via_ses(message)
            elif self.provider == 'resend':
                return await self._send_via_resend(message)
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported email provider: {self.provider}"
                }
                
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return {
                "status": "error",
                "message": f"Email sending failed: {str(e)}"
            }
    
    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        if self.provider == 'smtp':
            return all([self.smtp_host, self.smtp_username, self.smtp_password])
        elif self.provider == 'sendgrid':
            return self.api_key is not None
        elif self.provider == 'ses':
            return all([self.aws_access_key, self.aws_secret_key])
        elif self.provider == 'resend':
            return self.api_key is not None
        return False
    
    async def _send_via_smtp(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = message.from_email
            msg['To'] = message.to
            
            if message.reply_to:
                msg['Reply-To'] = message.reply_to
            
            # Add text part
            if message.text_body:
                text_part = MIMEText(message.text_body, 'plain')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(message.html_body, 'html')
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {message.to}")
            return {
                "status": "success",
                "message": f"Email sent to {message.to}",
                "provider": "smtp"
            }
            
        except Exception as e:
            logger.error(f"SMTP sending failed: {e}")
            raise
    
    async def _send_via_sendgrid(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via SendGrid API"""
        try:
            from backend.core.http_client import get_http_client
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "personalizations": [{"to": [{"email": message.to}]}],
                "from": {"email": message.from_email},
                "subject": message.subject,
                "content": [
                    {"type": "text/html", "value": message.html_body}
                ]
            }
            
            if message.text_body:
                data["content"].append({"type": "text/plain", "value": message.text_body})
            
            client = await get_http_client()
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            logger.info(f"Email sent via SendGrid to {message.to}")
            return {
                "status": "success",
                "message": f"Email sent to {message.to}",
                "provider": "sendgrid",
                "message_id": response.headers.get('X-Message-Id')
            }
            
        except Exception as e:
            logger.error(f"SendGrid sending failed: {e}")
            raise
    
    async def _send_via_ses(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via AWS SES"""
        try:
            import boto3
            
            ses = boto3.client(
                'ses',
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            response = ses.send_email(
                Source=message.from_email,
                Destination={'ToAddresses': [message.to]},
                Message={
                    'Subject': {'Data': message.subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': message.html_body, 'Charset': 'UTF-8'},
                        'Text': {'Data': message.text_body or '', 'Charset': 'UTF-8'}
                    }
                }
            )
            
            logger.info(f"Email sent via SES to {message.to}")
            return {
                "status": "success",
                "message": f"Email sent to {message.to}",
                "provider": "ses",
                "message_id": response['MessageId']
            }
            
        except Exception as e:
            logger.error(f"SES sending failed: {e}")
            raise
    
    async def _send_via_resend(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via Resend API"""
        try:
            from backend.core.http_client import get_http_client
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "from": message.from_email,
                "to": [message.to],
                "subject": message.subject,
                "html": message.html_body
            }
            
            if message.text_body:
                data["text"] = message.text_body
                
            if message.reply_to:
                data["reply_to"] = message.reply_to
            
            client = await get_http_client()
            response = await client.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Email sent via Resend to {message.to}")
            return {
                "status": "success",
                "message": f"Email sent to {message.to}",
                "provider": "resend",
                "message_id": result.get('id')
            }
            
        except Exception as e:
            logger.error(f"Resend sending failed: {e}")
            raise

# Email template helpers
class EmailTemplates:
    """Predefined email templates"""
    
    @staticmethod
    def password_reset(reset_url: str, user_name: str) -> EmailMessage:
        """Password reset email template"""
        subject = "Reset Your Password"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Password Reset Request</h2>
            <p>Hi {user_name},</p>
            <p>You requested a password reset for your account. Click the button below to reset your password:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background-color: #007cba; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                    Reset Password
                </a>
            </p>
            <p>If you didn't request this, please ignore this email.</p>
            <p>This link will expire in 24 hours.</p>
            <p>Best regards,<br>The Social Media Team</p>
        </body>
        </html>
        """
        
        text_body = f"""
        Hi {user_name},
        
        You requested a password reset for your account.
        Click the link below to reset your password:
        
        {reset_url}
        
        If you didn't request this, please ignore this email.
        This link will expire in 24 hours.
        
        Best regards,
        The Social Media Team
        """
        
        return EmailMessage(
            to="",  # Will be set when sending
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    @staticmethod
    def organization_invitation(org_name: str, invited_by: str, join_url: str) -> EmailMessage:
        """Organization invitation email template"""
        subject = f"You've been invited to join {org_name}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Organization Invitation</h2>
            <p>Hi there,</p>
            <p>{invited_by} has invited you to join <strong>{org_name}</strong> on our social media platform.</p>
            <p>Click the button below to accept the invitation and get started:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{join_url}" style="background-color: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                    Join Organization
                </a>
            </p>
            <p>If you don't want to join this organization, you can safely ignore this email.</p>
            <p>Best regards,<br>The Social Media Team</p>
        </body>
        </html>
        """
        
        text_body = f"""
        Hi there,
        
        {invited_by} has invited you to join {org_name} on our social media platform.
        
        Click the link below to accept the invitation:
        {join_url}
        
        If you don't want to join this organization, you can safely ignore this email.
        
        Best regards,
        The Social Media Team
        """
        
        return EmailMessage(
            to="",  # Will be set when sending
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    @staticmethod
    def email_verification(verification_url: str, user_name: str) -> EmailMessage:
        """Email verification template"""
        subject = "Verify Your Email - AI Social Media Agent"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1>Welcome to AI Social Media Agent!</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2>Hi {user_name},</h2>
                <p>Thanks for signing up! Please verify your email address to get started with our AI-powered social media management platform.</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Verify Email Address
                    </a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #fff; padding: 10px; border: 1px solid #ddd; font-family: monospace; font-size: 12px;">
                    {verification_url}
                </p>
                <p><strong>This link expires in 24 hours.</strong></p>
                <hr style="margin: 30px 0; border: none; height: 1px; background: #ddd;">
                <p style="font-size: 12px; color: #666; text-align: center;">
                    If you didn't create an account, you can safely ignore this email.<br>
                    &copy; 2025 AI Social Media Agent. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to AI Social Media Agent!
        
        Hi {user_name},
        
        Thanks for signing up! Please verify your email address by visiting:
        {verification_url}
        
        This link expires in 24 hours.
        
        If you didn't create an account, you can safely ignore this email.
        
        Best regards,
        The AI Social Media Agent Team
        """
        
        return EmailMessage(
            to="",  # Will be set when sending
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

# Convenience methods for the EmailService
class EmailServiceMethods:
    """Additional methods for the email service"""
    
    @staticmethod
    async def send_verification_email(to_email: str, username: str, verification_token: str):
        """Send email verification using existing service"""
        from backend.core.config import get_settings
        settings = get_settings()
        
        frontend_url = getattr(settings, 'frontend_url', 'https://lily-ai-socialmedia.com')
        verification_url = f"{frontend_url}/verify-email?token={verification_token}"
        
        template = EmailTemplates.email_verification(verification_url, username)
        template.to = to_email
        
        service = EmailService()
        return await service.send_email(template)
    
    @staticmethod
    async def send_password_reset_email(to_email: str, username: str, reset_token: str):
        """Send password reset using existing service"""
        from backend.core.config import get_settings
        settings = get_settings()
        
        frontend_url = getattr(settings, 'frontend_url', 'https://lily-ai-socialmedia.com')
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"
        
        template = EmailTemplates.password_reset(reset_url, username)
        template.to = to_email
        
        service = EmailService()
        return await service.send_email(template)

# Global email service instance
email_service = EmailService()
email_methods = EmailServiceMethods()
