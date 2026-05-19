"""Comment PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.config import settings


class ArticleDateIndex(GlobalSecondaryIndex):
    """Index for querying comments by article and date."""

    class Meta:
        index_name = "article-date-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    article_id = UnicodeAttribute(hash_key=True)
    created_at = NumberAttribute(range_key=True)


class CommentModel(Model):
    """Comment model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}comments"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    comment_id = UnicodeAttribute(hash_key=True)

    # Indexes
    article_date_index = ArticleDateIndex()

    # Attributes
    article_id = UnicodeAttribute()
    user_id = UnicodeAttribute()
    content = UnicodeAttribute()
    created_at = NumberAttribute()
    updated_at = NumberAttribute()
