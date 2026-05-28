"""Chat models for conversation sessions, messages, and user preferences."""

from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    BooleanAttribute,
    ListAttribute,
    MapAttribute,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.config import settings


class UserLastMessageIndex(GlobalSecondaryIndex):
    """Index for querying conversation sessions by user and last message time."""

    class Meta:
        index_name = "user-last-message-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    user_id = UnicodeAttribute(hash_key=True)
    last_message_at = NumberAttribute(range_key=True)


class SessionTimestampIndex(GlobalSecondaryIndex):
    """Index for querying conversation messages by session and timestamp."""

    class Meta:
        index_name = "session-timestamp-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    session_id = UnicodeAttribute(hash_key=True)
    timestamp = NumberAttribute(range_key=True)


class ConversationSessionModel(Model):
    """Conversation session model stored in DynamoDB.

    Represents a chat conversation session between a user and the AI.
    Sessions have a 90-day TTL and are queryable by user and last message time.
    """

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}conversation_sessions"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys (composite: user_id as hash, session_id as range)
    user_id = UnicodeAttribute(hash_key=True)
    session_id = UnicodeAttribute(range_key=True)

    # Indexes
    user_last_message_index = UserLastMessageIndex()

    # Attributes
    title = UnicodeAttribute()  # Session title (e.g., "Tech News Discussion")
    description = UnicodeAttribute(null=True)  # Optional session description
    last_message_at = NumberAttribute()  # Unix timestamp of last message
    created_at = NumberAttribute()  # Unix timestamp of session creation
    updated_at = NumberAttribute()  # Unix timestamp of last update
    message_count = NumberAttribute(default=0)  # Total messages in session
    is_active = BooleanAttribute(default=True)  # Whether session is active

    # TTL: 90 days (7776000 seconds)
    expires_at = NumberAttribute(null=True)  # Unix timestamp for TTL expiration


class ConversationMessageModel(Model):
    """Conversation message model stored in DynamoDB.

    Represents individual messages within a conversation session.
    Messages have a 90-day TTL and are queryable by session and timestamp.
    """

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}conversation_messages"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys (composite: session_id as hash, message_id as range)
    session_id = UnicodeAttribute(hash_key=True)
    message_id = UnicodeAttribute(range_key=True)

    # Indexes
    session_timestamp_index = SessionTimestampIndex()

    # Attributes
    user_id = UnicodeAttribute()  # User who sent/owned this message
    role = UnicodeAttribute()  # "user" or "assistant"
    content = UnicodeAttribute()  # Message text content
    timestamp = NumberAttribute()  # Unix timestamp of message creation

    # Optional metadata
    token_count = NumberAttribute(null=True)  # LLM token count if from assistant
    model_used = UnicodeAttribute(null=True)  # Model that generated response

    # TTL: 90 days (7776000 seconds)
    expires_at = NumberAttribute(null=True)  # Unix timestamp for TTL expiration


class ChatUserPreferencesModel(Model):
    """Chat user preferences model stored in DynamoDB.

    Stores user-specific preferences for chat behavior and display.
    This is permanent data with no TTL.
    """

    class Meta:
        table_name = f"{settings.dynamodb_table_prefix}chat_user_preferences"
        region = settings.aws_region
        host = settings.dynamodb_endpoint_url
        read_capacity_units = 5
        write_capacity_units = 5

    # Keys
    user_id = UnicodeAttribute(hash_key=True)

    # Preferences
    theme = UnicodeAttribute(default="light")  # "light" or "dark"
    font_size = UnicodeAttribute(default="medium")  # "small", "medium", "large"

    # Chat behavior
    auto_save_enabled = BooleanAttribute(default=True)  # Auto-save conversations
    notification_enabled = BooleanAttribute(default=False)  # Desktop notifications
    typing_indicator_enabled = BooleanAttribute(default=True)  # Show typing indicator

    # LLM settings
    temperature = NumberAttribute(default=0.7)  # LLM temperature (0.0-2.0)
    max_tokens = NumberAttribute(default=2048)  # Max tokens per response

    # Display preferences
    show_token_count = BooleanAttribute(default=False)  # Display token counts
    compact_mode = BooleanAttribute(default=False)  # Compact message display

    # Timestamps
    created_at = NumberAttribute()  # Unix timestamp of preference creation
    updated_at = NumberAttribute()  # Unix timestamp of last update
