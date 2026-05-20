"""Model for pending Tavily search results awaiting admin review."""

from pynamodb.attributes import UnicodeAttribute, NumberAttribute, ListAttribute
from pynamodb.models import Model

from app.config import settings


class PendingSearchModel(Model):
    """Pending search result from Tavily awaiting admin review and approval."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}pending-searches"
        region = settings.aws_region
        if settings.dynamodb_endpoint_url:
            host = settings.dynamodb_endpoint_url

    # Primary key
    search_id = UnicodeAttribute(hash_key=True)

    # Search metadata
    query = UnicodeAttribute()  # What was searched (e.g., "artificial intelligence")
    title = UnicodeAttribute()  # Result title from Tavily
    url = UnicodeAttribute()  # Source URL
    snippet = UnicodeAttribute(null=True)  # Description/snippet from Tavily
    source = UnicodeAttribute(null=True)  # Source domain

    # Timestamps
    created_at = NumberAttribute()  # When search result was added
    updated_at = NumberAttribute()  # When it was last updated

    # Status
    status = UnicodeAttribute(default="pending")  # pending, approved, rejected

    # Optional: track which admin approved it
    approved_by = UnicodeAttribute(null=True)
    approved_at = NumberAttribute(null=True)
