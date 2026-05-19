"""Create test admin and user accounts in DynamoDB.

Usage:
    python scripts/create_test_accounts.py

Creates:
    - Admin account: admin / admin@example.com / admin123
    - User account: testuser / user@example.com / user123
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.user import UserModel
from app.core.security import hash_password
from app.utils.time import now_timestamp


async def create_test_accounts():
    """Create test admin and user accounts."""
    print("[+] Creating test accounts...")

    admin_password = "admin123"
    user_password = "user123"

    try:
        # Check if admin already exists
        try:
            existing_admin = UserModel.get("admin-user-1")
            print("[OK] Admin account already exists (admin@example.com)")
        except:
            # Create admin account
            admin = UserModel(
                user_id="admin-user-1",
                username="admin",
                email="admin@example.com",
                password_hash=hash_password(admin_password),
                is_admin=True,
                is_active=True,
                created_at=now_timestamp(),
                updated_at=now_timestamp(),
            )
            admin.save()
            print("[OK] Admin account created:")
            print(f"     Username: admin")
            print(f"     Email: admin@example.com")
            print(f"     Password: admin123")
            print(f"     Is Admin: True")

        # Check if user already exists
        try:
            existing_user = UserModel.get("test-user-1")
            print("[OK] Test user account already exists (user@example.com)")
        except:
            # Create user account
            user = UserModel(
                user_id="test-user-1",
                username="testuser",
                email="user@example.com",
                password_hash=hash_password(user_password),
                is_admin=False,
                is_active=True,
                created_at=now_timestamp(),
                updated_at=now_timestamp(),
            )
            user.save()
            print("[OK] Test user account created:")
            print(f"     Username: testuser")
            print(f"     Email: user@example.com")
            print(f"     Password: user123")
            print(f"     Is Admin: False")

        print("\n[SUCCESS] Test accounts ready for use!")
        print("\nLogin with:")
        print('  Admin: POST /v1/auth/login {"username": "admin", "password": "admin123"}')
        print('  User:  POST /v1/auth/login {"username": "testuser", "password": "user123"}')

    except Exception as e:
        print(f"[ERROR] Error creating test accounts: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_test_accounts())
