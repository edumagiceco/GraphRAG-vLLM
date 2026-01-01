#!/usr/bin/env python3
"""
Admin user creation script.

This script creates an initial admin user with secure credentials.
Run this after first deployment instead of relying on auto-creation.

Usage:
    # Interactive mode (prompts for password)
    python scripts/create_admin.py

    # Non-interactive mode (uses environment variables)
    ADMIN_EMAIL=admin@company.com ADMIN_PASSWORD=SecureP@ss123 python scripts/create_admin.py

    # Force recreate (updates existing user's password)
    python scripts/create_admin.py --force
"""
import asyncio
import getpass
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select


async def create_admin(email: str, password: str, force: bool = False) -> bool:
    """
    Create or update admin user.

    Args:
        email: Admin email
        password: Admin password
        force: If True, update existing user's password

    Returns:
        True if user was created/updated, False otherwise
    """
    from src.core.database import async_session_maker, init_db
    from src.models.admin_user import AdminUser
    from src.services.auth_service import AuthService

    # Initialize database
    await init_db()

    async with async_session_maker() as session:
        # Check if user exists
        result = await session.execute(
            select(AdminUser).where(AdminUser.email == email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if force:
                # Update password
                existing_user.hashed_password = AuthService.hash_password(password)
                await session.commit()
                print(f"✓ Updated password for existing admin: {email}")
                return True
            else:
                print(f"✗ Admin user already exists: {email}")
                print("  Use --force to update the password")
                return False

        # Create new admin
        admin = await AuthService.create_user(
            db=session,
            email=email,
            password=password,
        )

        if admin:
            print(f"✓ Created admin user: {email}")
            return True
        else:
            print("✗ Failed to create admin user")
            return False


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    from src.services.auth_service import AuthService
    return AuthService.validate_password_strength(password)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create or update admin user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing user's password",
    )
    parser.add_argument(
        "--email",
        help="Admin email (or set ADMIN_EMAIL env var)",
    )
    parser.add_argument(
        "--password",
        help="Admin password (or set ADMIN_PASSWORD env var, or enter interactively)",
    )
    args = parser.parse_args()

    # Get email
    email = args.email or os.getenv("ADMIN_EMAIL")
    if not email:
        email = input("Enter admin email: ").strip()
        if not email:
            print("✗ Email is required")
            sys.exit(1)

    # Get password
    password = args.password or os.getenv("ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Enter admin password: ")
        if not password:
            print("✗ Password is required")
            sys.exit(1)

        # Confirm password
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("✗ Passwords do not match")
            sys.exit(1)

    # Validate password strength
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        print(f"✗ Password validation failed: {error_msg}")
        print("\nPassword requirements:")
        print("  - At least 8 characters")
        print("  - At least one uppercase letter")
        print("  - At least one lowercase letter")
        print("  - At least one digit")
        print("  - Not a common weak password")
        sys.exit(1)

    # Create admin
    success = asyncio.run(create_admin(email, password, args.force))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
