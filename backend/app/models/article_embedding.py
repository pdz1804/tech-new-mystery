"""Article embedding PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    ListAttribute,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.config import settings


class ModelIndex(GlobalSecondaryIndex):
    """Index for querying embeddings by model."""

    class Meta:
        index_name = "model-timestamp-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    model = UnicodeAttribute(hash_key=True)
    timestamp = NumberAttribute(range_key=True)


class ArticleEmbeddingModel(Model):
    """Article embedding model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}article-embeddings"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    article_id = UnicodeAttribute(hash_key=True)

    # Indexes
    model_index = ModelIndex()

    # Attributes
    embedding = ListAttribute(of=NumberAttribute)
    model = UnicodeAttribute()
    timestamp = NumberAttribute()
