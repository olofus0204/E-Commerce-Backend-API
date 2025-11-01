"""
Authentication service.
Business logic for user registration, login, token management, and logout.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from jose import JWTError

from app.models.user import User, RefreshToken, UserRole
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.core.exceptions import ValidationError, AuthenticationError, AuthorizationError, ConflictError
from app.core.config import settings


class AuthService:
    """Service class for authentication operations."""

    def __init__(self, db: Session):
        self.db = db

    def register(self, email: str, password: str, full_name: str = None) -> dict:
        """
        Register a new user.

        Args:
            email: User email address
            password: Plain text password
            full_name: Optional full name

        Returns:
            dict with user and tokens

        Raises:
            ConflictError: If email already exists
        """
        # Check if email already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ConflictError("Email already exists")

        # Create new user with hashed password
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole.customer  # Default role
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token_str = create_refresh_token(str(user.id))

        # Store refresh token in database
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        self.db.add(refresh_token)
        self.db.commit()

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token_str
        }

    def login(self, email: str, password: str) -> dict:
        """
        Authenticate user and generate tokens.

        Args:
            email: User email
            password: Plain text password

        Returns:
            dict with user and tokens

        Raises:
            ValidationError: If email or password is missing
            AuthenticationError: If credentials are invalid
            AuthorizationError: If account is inactive
        """
        if not email or not password:
            raise ValidationError("Email and password are required")

        # Get user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise AuthenticationError("Invalid credentials")

        # Verify password
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")

        # Check if account is active
        if not user.is_active:
            raise AuthorizationError("Account is inactive")

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token_str = create_refresh_token(str(user.id))

        # Store refresh token in database
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        self.db.add(refresh_token)
        self.db.commit()

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token_str
        }

    def refresh_tokens(self, refresh_token_str: str) -> dict:
        """
        Generate new access and refresh tokens using a valid refresh token.

        Args:
            refresh_token_str: Current refresh token

        Returns:
            dict with new access_token and refresh_token

        Raises:
            ValidationError: If refresh token is missing
            AuthenticationError: If token is invalid or expired
            AuthorizationError: If token has been revoked
        """
        if not refresh_token_str:
            raise ValidationError("Refresh token is required")

        try:
            # Verify token signature and expiration
            payload = verify_token(refresh_token_str, token_type="refresh")
            user_id = payload.get("sub")

            if not user_id:
                raise AuthenticationError("Invalid token payload")

            # Check if token exists in database (not revoked)
            stored_token = self.db.query(RefreshToken).filter(
                RefreshToken.token == refresh_token_str
            ).first()

            if not stored_token:
                raise AuthorizationError("Token has been revoked")

            # Check if token is expired
            if stored_token.expires_at < datetime.utcnow():
                # Delete expired token
                self.db.delete(stored_token)
                self.db.commit()
                raise AuthenticationError("Refresh token expired")

            # Delete old refresh token
            self.db.delete(stored_token)

            # Generate new tokens
            new_access_token = create_access_token(user_id)
            new_refresh_token = create_refresh_token(user_id)

            # Store new refresh token
            refresh_token = RefreshToken(
                user_id=user_id,
                token=new_refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            )
            self.db.add(refresh_token)
            self.db.commit()

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            }

        except JWTError:
            raise AuthenticationError("Invalid or expired refresh token")

    def logout(self, refresh_token_str: str) -> None:
        """
        Revoke refresh token (logout user).

        Args:
            refresh_token_str: Refresh token to revoke

        Raises:
            ValidationError: If refresh token is missing
        """
        if not refresh_token_str:
            raise ValidationError("Refresh token is required")

        # Find and delete refresh token
        token = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str
        ).first()

        if token:
            self.db.delete(token)
            self.db.commit()
