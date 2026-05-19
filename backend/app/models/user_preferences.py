"""User Preferences PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, BooleanAttribute, NumberAttribute, ListAttribute

from app.config import settings


class UserPreferencesModel(Model):
    """User preferences model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}user_preferences"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    user_id = UnicodeAttribute(hash_key=True)

    # Attributes
    topics = ListAttribute(of=UnicodeAttribute, default=list)
    sources = ListAttribute(of=UnicodeAttribute, default=list)
    notification_enabled = BooleanAttribute(default=False)
    digest_frequency = UnicodeAttribute(default="daily")
    theme = UnicodeAttribute(default="light")
    # Email digest settings
    email_digest_enabled = BooleanAttribute(default=False)
    email_digest_frequency = UnicodeAttribute(default="daily")
    created_at = NumberAttribute()
    updated_at = NumberAttribute()
