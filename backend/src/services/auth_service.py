"""
Authentication service for JWT token management.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.admin_user import AdminUser

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Minimum password requirements
MIN_PASSWORD_LENGTH = 8
COMMON_WEAK_PASSWORDS = {
    "admin123", "password", "123456", "password123", "admin",
    "12345678", "qwerty", "abc123", "letmein", "welcome",
}


class AuthService:
    """Authentication service for user management and JWT tokens."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain password."""
        return pwd_context.hash(password)

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password strength.

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - Not in common weak password list

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"

        if password.lower() in COMMON_WEAK_PASSWORDS:
            return False, "Password is too common. Please choose a stronger password"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        return True, ""

    @staticmethod
    def is_password_secure(password: str) -> bool:
        """
        Check if password meets security requirements.

        Args:
            password: Password to check

        Returns:
            True if password is secure, False otherwise
        """
        is_valid, _ = AuthService.validate_password_strength(password)
        return is_valid

    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload data to encode
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Optional[AdminUser]:
        """
        Authenticate a user by email and password.

        Args:
            db: Database session
            email: User email
            password: Plain password

        Returns:
            AdminUser if authenticated, None otherwise
        """
        # Find user by email
        result = await db.execute(
            select(AdminUser).where(AdminUser.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Verify password
        if not AuthService.verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: str,
    ) -> Optional[AdminUser]:
        """
        Get user by ID.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            AdminUser if found, None otherwise
        """
        result = await db.execute(
            select(AdminUser).where(AdminUser.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str,
    ) -> Optional[AdminUser]:
        """
        Get user by email.

        Args:
            db: Database session
            email: User email

        Returns:
            AdminUser if found, None otherwise
        """
        result = await db.execute(
            select(AdminUser).where(AdminUser.email == email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> AdminUser:
        """
        Create a new admin user.

        Args:
            db: Database session
            email: User email
            password: Plain password

        Returns:
            Created AdminUser
        """
        hashed_password = AuthService.hash_password(password)

        user = AdminUser(
            email=email,
            password_hash=hashed_password,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def create_initial_admin(db: AsyncSession) -> Optional[AdminUser]:
        """
        Create initial admin user from environment variables.
        Only creates if no admin users exist.

        Args:
            db: Database session

        Returns:
            Created AdminUser or None if already exists
        """
        # Check if any admin exists
        result = await db.execute(select(AdminUser).limit(1))
        if result.scalar_one_or_none():
            return None

        # Create initial admin from settings
        return await AuthService.create_user(
            db=db,
            email=settings.admin_email,
            password=settings.admin_password,
        )
