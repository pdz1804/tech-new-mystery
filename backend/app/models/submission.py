"""Submission PynamoDB model."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.config import settings


class UserDateIndex(GlobalSecondaryIndex):
    """Index for querying submissions by user and date."""

    class Meta:
        index_name = "user-date-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    user_id = UnicodeAttribute(hash_key=True)
    submitted_at = NumberAttribute(range_key=True)


class SubmissionModel(Model):
    """Submission model stored in DynamoDB."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}submissions"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    submission_id = UnicodeAttribute(hash_key=True)

    # Indexes
    user_date_index = UserDateIndex()

    # Attributes
    user_id = UnicodeAttribute()
    url = UnicodeAttribute()
    status = UnicodeAttribute(default="pending")
    article_id = UnicodeAttribute(null=True)
    error_message = UnicodeAttribute(null=True)
    submitted_at = NumberAttribute()
    processed_at = NumberAttribute(null=True)
