"""
User profile routes.
API endpoints for managing user profiles.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.services.user_service import UserService
from app.schemas.user import UserDetailResponse, UserUpdate, DeleteAccountRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user's profile.

    Requires valid access token.

    Returns complete user profile information.
    """
    return UserDetailResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put("/me", response_model=UserDetailResponse)
async def update_current_user_profile(
    request: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.

    Requires valid access token.

    - **full_name**: New full name (optional)
    - **email**: New email address (requires current_password)
    - **current_password**: Current password (required for email/password changes)
    - **new_password**: New password (requires current_password)

    Returns updated user profile.
    """
    service = UserService(db)
    updated_user = service.update_user_profile(
        user=current_user,
        full_name=request.full_name,
        email=request.email,
        current_password=request.current_password,
        new_password=request.new_password
    )

    return UserDetailResponse(
        id=str(updated_user.id),
        email=updated_user.email,
        full_name=updated_user.full_name,
        role=updated_user.role.value,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at
    )


@router.delete("/me")
async def delete_current_user_account(
    request: DeleteAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete current user's account (soft delete).

    Requires valid access token.

    - **password**: Password confirmation

    Sets account to inactive (is_active=False).
    Returns success message.
    """
    service = UserService(db)
    service.delete_user_account(current_user, request.password)

    return {"message": "Account deleted successfully"}
