"""
Email service for sending digest emails.
Uses SMTP for email delivery (configurable via environment).
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@technewsmystery.com")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send an email with HTML and optional text content."""
        try:
            # For development, just log instead of sending
            if self.smtp_host == "localhost" or not self.smtp_user:
                logger.info(f"[DEV MODE] Email to {to_email}: {subject}")
                logger.info(f"[DEV MODE] Content: {html_content[:100]}...")
                return True

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Attach text version
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))

            # Attach HTML version
            msg.attach(MIMEText(html_content, "html"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_digest_email(
        self,
        to_email: str,
        username: str,
        articles: list,
        digest_type: str = "daily",
    ) -> bool:
        """Send a news digest email."""
        subject = f"Tech News Mystery - {digest_type.title()} Digest"

        # Build HTML content
        article_html = ""
        for article in articles:
            article_html += f"""
            <div style="margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; color: #333;">
                    <a href="http://localhost:3000/articles/{article.get('slug')}" style="color: #0066cc; text-decoration: none;">
                        {article.get('title')}
                    </a>
                </h3>
                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">
                    {article.get('published_at', 'Recently published')} |
                    Category: <strong>{article.get('category', 'General')}</strong>
                </p>
                <p style="margin: 0; color: #555; line-height: 1.6;">
                    {article.get('summary', article.get('content', '')[:200])}...
                </p>
            </div>
            """

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <div style="background-color: #0066cc; color: white; padding: 20px; text-align: center; border-radius: 5px; margin-bottom: 30px;">
                        <h1 style="margin: 0;">Tech News Mystery</h1>
                        <p style="margin: 10px 0 0 0;">{digest_type.title()} Digest</p>
                    </div>

                    <p style="margin: 0 0 20px 0;">Hi {username},</p>
                    <p style="margin: 0 0 20px 0;">
                        Here are your personalized tech news stories from today:
                    </p>

                    {article_html}

                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-top: 30px;">
                        <p style="margin: 0 0 10px 0;">
                            <a href="http://localhost:3000/" style="color: #0066cc; text-decoration: none;">
                                View all articles →
                            </a>
                        </p>
                        <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                            <a href="http://localhost:3000/profile" style="color: #0066cc; text-decoration: none;">
                                Manage your preferences
                            </a>
                        </p>
                    </div>

                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="margin: 0; font-size: 12px; color: #999;">
                        © 2026 Tech News Mystery. All rights reserved.
                    </p>
                </div>
            </body>
        </html>
        """

        return self.send_email(to_email, subject, html_content)


email_service = EmailService()
