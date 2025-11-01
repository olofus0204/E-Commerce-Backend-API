"""
User service.
Business logic for user profile management.
"""

from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import hash_password, verify_password
from app.core.exceptions import ValidationError, AuthenticationError, ConflictError


class UserService:
    """Service class for user profile operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_profile(self, user_id: str) -> User:
        """
        Get user profile by ID.

        Args:
            user_id: User UUID as string

        Returns:
            User object

        Raises:
            ValidationError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValidationError("User not found")
        return user

    def update_user_profile(
        self,
        user: User,
        full_name: str = None,
        email: str = None,
        current_password: str = None,
        new_password: str = None
    ) -> User:
        """
        Update user profile information.

        Args:
            user: Current user object
            full_name: New full name
            email: New email address
            current_password: Current password (required for email/password changes)
            new_password: New password

        Returns:
            Updated User object

        Raises:
            AuthenticationError: If current password is incorrect
            ConflictError: If new email already exists
            ValidationError: If current_password missing for sensitive changes
        """
        # Check if sensitive changes require current password
        if (email or new_password) and not current_password:
            raise ValidationError("Current password required for email or password changes")

        # Verify current password if provided
        if current_password:
            if not verify_password(current_password, user.password_hash):
                raise AuthenticationError("Incorrect current password")

        # Update full name
        if full_name is not None:
            user.full_name = full_name

        # Update email
        if email and email != user.email:
            # Check if email already exists
            existing_user = self.db.query(User).filter(User.email == email).first()
            if existing_user:
                raise ConflictError("Email already exists")
            user.email = email

        # Update password
        if new_password:
            user.password_hash = hash_password(new_password)

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user_account(self, user: User, password: str) -> None:
        """
        Soft delete user account (set is_active=False).

        Args:
            user: User object to delete
            password: Password confirmation

        Raises:
            AuthenticationError: If password is incorrect
        """
        # Verify password
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Incorrect password")

        # Soft delete (set inactive)
        user.is_active = False
        self.db.commit()
