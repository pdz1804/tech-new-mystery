"""System-wide settings stored in DynamoDB."""

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute

from app.config import settings


class SystemSettingsModel(Model):
    """Store system-wide settings like quality score threshold."""

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}system-settings"
        region = settings.aws_region
        if settings.dynamodb_endpoint_url:
            host = settings.dynamodb_endpoint_url
        read_capacity_units = 1
        write_capacity_units = 1

    setting_key = UnicodeAttribute(hash_key=True)
    value_number = NumberAttribute(null=True)
    value_text = UnicodeAttribute(null=True)
    updated_at = NumberAttribute()
