"""News Source PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, BooleanAttribute, NumberAttribute

from app.config import settings


class NewsSourceModel(Model):
    """News source model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}news_sources"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    source_id = UnicodeAttribute(hash_key=True)

    # Attributes
    name = UnicodeAttribute()
    url = UnicodeAttribute()
    feed_url = UnicodeAttribute(null=True)
    category = UnicodeAttribute(null=True)
    priority = NumberAttribute(default=5)
    enabled = BooleanAttribute(default=True)
    last_crawled_at = NumberAttribute(null=True)
    created_at = NumberAttribute()
