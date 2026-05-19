"""
Celery tasks for sending email digests.
"""

from celery import shared_task
import logging
from datetime import datetime, timedelta
from app.integrations.email_service import email_service
from app.repositories.user_repository import UserRepository
from app.repositories.article_repository import ArticleRepository
from app.repositories.user_preferences_repository import UserPreferencesRepository

logger = logging.getLogger(__name__)

user_repo = UserRepository()
article_repo = ArticleRepository()
prefs_repo = UserPreferencesRepository()


@shared_task(bind=True, max_retries=3)
def send_daily_digest(self):
    """Generate and send daily digest emails to subscribed users."""
    try:
        logger.info("Starting daily digest generation...")

        # Get all users with daily digest enabled
        users = user_repo.get_all_users()

        digest_count = 0
        for user in users:
            # Check if user has daily digest enabled
            prefs = prefs_repo.get_user_preferences(user.get("user_id"))

            if not prefs or not prefs.get("email_digest_enabled") or prefs.get("email_digest_frequency") != "daily":
                continue

            # Get articles from the last 24 hours
            articles = article_repo.get_articles_by_date_range(
                start_date=datetime.utcnow() - timedelta(days=1),
                end_date=datetime.utcnow(),
                limit=10,
            )

            if not articles:
                continue

            # Send email
            success = email_service.send_digest_email(
                to_email=user.get("email"),
                username=user.get("username"),
                articles=articles,
                digest_type="daily",
            )

            if success:
                digest_count += 1
                logger.info(f"Daily digest sent to {user.get('email')}")
            else:
                logger.error(f"Failed to send daily digest to {user.get('email')}")

        logger.info(f"Daily digest generation complete. Sent {digest_count} emails.")
        return {"success": True, "sent_count": digest_count}

    except Exception as exc:
        logger.error(f"Error in send_daily_digest: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes


@shared_task(bind=True, max_retries=3)
def send_weekly_digest(self):
    """Generate and send weekly digest emails to subscribed users."""
    try:
        logger.info("Starting weekly digest generation...")

        # Get all users with weekly digest enabled
        users = user_repo.get_all_users()

        digest_count = 0
        for user in users:
            # Check if user has weekly digest enabled
            prefs = prefs_repo.get_user_preferences(user.get("user_id"))

            if not prefs or not prefs.get("email_digest_enabled") or prefs.get("email_digest_frequency") != "weekly":
                continue

            # Get articles from the last 7 days
            articles = article_repo.get_articles_by_date_range(
                start_date=datetime.utcnow() - timedelta(days=7),
                end_date=datetime.utcnow(),
                limit=20,
            )

            if not articles:
                continue

            # Send email
            success = email_service.send_digest_email(
                to_email=user.get("email"),
                username=user.get("username"),
                articles=articles,
                digest_type="weekly",
            )

            if success:
                digest_count += 1
                logger.info(f"Weekly digest sent to {user.get('email')}")
            else:
                logger.error(f"Failed to send weekly digest to {user.get('email')}")

        logger.info(f"Weekly digest generation complete. Sent {digest_count} emails.")
        return {"success": True, "sent_count": digest_count}

    except Exception as exc:
        logger.error(f"Error in send_weekly_digest: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes


@shared_task
def send_test_digest(user_email: str, user_name: str = "User"):
    """Send a test digest email (for testing purposes)."""
    try:
        logger.info(f"Sending test digest to {user_email}...")

        # Get recent articles
        articles = article_repo.get_articles(limit=5)

        if not articles:
            logger.warning("No articles available for test digest")
            return {"success": False, "error": "No articles found"}

        # Send email
        success = email_service.send_digest_email(
            to_email=user_email,
            username=user_name,
            articles=articles,
            digest_type="test",
        )

        if success:
            logger.info(f"Test digest sent to {user_email}")
            return {"success": True, "email": user_email}
        else:
            logger.error(f"Failed to send test digest to {user_email}")
            return {"success": False, "error": "Failed to send email"}

    except Exception as exc:
        logger.error(f"Error in send_test_digest: {str(exc)}")
        return {"success": False, "error": str(exc)}
