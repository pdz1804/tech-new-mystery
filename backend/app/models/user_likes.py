"""User Likes PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute

from app.config import settings


class UserLikesModel(Model):
    """User liked articles model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}user_likes"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys (composite key)
    user_id = UnicodeAttribute(hash_key=True)
    article_id = UnicodeAttribute(range_key=True)

    # Attributes
    liked_at = NumberAttribute()
