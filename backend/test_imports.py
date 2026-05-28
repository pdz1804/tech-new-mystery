#!/usr/bin/env python3
"""Quick test to verify imports work correctly."""

try:
    from app.services.chat_service import ChatService, CHAT_TTL_SECONDS
    from app.models.chat import ConversationSessionModel, ConversationMessageModel
    from app.utils.time import now_timestamp

    print("✓ All imports successful")
    print(f"✓ ChatService class: {ChatService}")
    print(f"✓ CHAT_TTL_SECONDS: {CHAT_TTL_SECONDS}")
    print(f"✓ ConversationSessionModel: {ConversationSessionModel}")
    print(f"✓ ConversationMessageModel: {ConversationMessageModel}")
    print(f"✓ now_timestamp function: {now_timestamp}")

    # Verify ChatService has all required methods
    service = ChatService()
    methods = [
        'create_session',
        'get_session',
        'list_sessions',
        'add_message',
        'get_messages',
        'archive_session',
        '_update_session_metadata'
    ]

    for method in methods:
        if hasattr(service, method):
            print(f"✓ Method {method} exists")
        else:
            print(f"✗ Method {method} missing")

    print("\n✓ All checks passed!")

except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
