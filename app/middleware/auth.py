"""
Authentication and authorization middleware.
Provides dependency functions for JWT token validation and role-based access control.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db
from app.core.security import verify_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User, UserRole


async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate JWT access token from Authorization header.
    Returns the authenticated User object.

    Args:
        authorization: Authorization header with Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        AuthenticationError: If token is invalid, expired, or user not found
    """
    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Invalid authorization header format")

    token = authorization.replace("Bearer ", "")

    try:
        # Verify and decode token
        payload = verify_token(token, token_type="access")
        user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationError("Invalid token payload")

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")

        return user

    except JWTError:
        raise AuthenticationError("Invalid or expired token")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify that the authenticated user is active.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User object

    Raises:
        AuthorizationError: If user account is inactive
    """
    if not current_user.is_active:
        raise AuthorizationError("Account is inactive")

    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Verify that the authenticated user has admin role.

    Args:
        current_user: User from get_current_active_user dependency

    Returns:
        User object

    Raises:
        AuthorizationError: If user is not an admin
    """
    if current_user.role != UserRole.admin:
        raise AuthorizationError("Admin privileges required")

    return current_user
