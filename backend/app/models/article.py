"""Article PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    BooleanAttribute,
    ListAttribute,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.config import settings


class SlugIndex(GlobalSecondaryIndex):
    """Index for looking up articles by slug."""

    class Meta:
        index_name = "slug-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    slug = UnicodeAttribute(hash_key=True)


class SourceDateIndex(GlobalSecondaryIndex):
    """Index for querying articles by source and date."""

    class Meta:
        index_name = "source-date-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    source_id = UnicodeAttribute(hash_key=True)
    published_at = NumberAttribute(range_key=True)


class ArticleModel(Model):
    """Article model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}articles"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    article_id = UnicodeAttribute(hash_key=True)

    # Indexes
    slug_index = SlugIndex()
    source_date_index = SourceDateIndex()

    # Attributes
    slug = UnicodeAttribute()
    title = UnicodeAttribute()
    source_id = UnicodeAttribute()
    original_url = UnicodeAttribute()
    preview_image = UnicodeAttribute(null=True)
    content = UnicodeAttribute(null=True)
    summary = UnicodeAttribute(null=True)
    markdown_content = UnicodeAttribute(null=True)
    author = UnicodeAttribute(null=True)
    category = UnicodeAttribute(null=True)
    tags = ListAttribute(of=UnicodeAttribute, default=list)
    is_published = BooleanAttribute(default=False)
    view_count = NumberAttribute(default=0)
    like_count = NumberAttribute(default=0)
    published_at = NumberAttribute(null=True)
    crawled_at = NumberAttribute(null=True)
    created_at = NumberAttribute()
    updated_at = NumberAttribute()
