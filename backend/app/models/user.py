"""User PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, BooleanAttribute, NumberAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.config import settings


class UsernameIndex(GlobalSecondaryIndex):
    """Index for looking up users by username."""

    class Meta:
        index_name = "username-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    username = UnicodeAttribute(hash_key=True)


class UserModel(Model):
    """User model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}users"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    user_id = UnicodeAttribute(hash_key=True)

    # Indexes
    username_index = UsernameIndex()

    # Attributes
    username = UnicodeAttribute()
    password_hash = UnicodeAttribute()
    email = UnicodeAttribute(null=True)
    is_admin = BooleanAttribute(default=False)
    is_active = BooleanAttribute(default=True)
    created_at = NumberAttribute()
    updated_at = NumberAttribute()
