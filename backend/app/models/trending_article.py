"""Trending Article PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute

from app.config import settings


class TrendingArticleModel(Model):
    """Trending articles model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}trending_articles"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    trending_id = UnicodeAttribute(hash_key=True)

    # Attributes
    article_id = UnicodeAttribute()
    score = NumberAttribute()
    rank = NumberAttribute()
    calculated_at = NumberAttribute()
    updated_at = NumberAttribute()
