"""
Authentication routes.
API endpoints for user registration, login, token refresh, and logout.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenResponse,
    LogoutRequest,
    UserResponse
)
from app.middleware.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Minimum 8 characters with uppercase, lowercase, and number
    - **full_name**: Optional full name

    Returns user data and authentication tokens.
    """
    service = AuthService(db)
    result = service.register(
        email=request.email,
        password=request.password,
        full_name=request.full_name
    )

    return RegisterResponse(
        user=UserResponse(
            id=str(result["user"].id),
            email=result["user"].email,
            full_name=result["user"].full_name,
            role=result["user"].role.value,
            created_at=result["user"].created_at
        ),
        access_token=result["access_token"],
        refresh_token=result["refresh_token"]
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and receive tokens.

    - **email**: User email address
    - **password**: User password

    Returns user data and authentication tokens.
    """
    service = AuthService(db)
    result = service.login(
        email=request.email,
        password=request.password
    )

    return LoginResponse(
        user=UserResponse(
            id=str(result["user"].id),
            email=result["user"].email,
            full_name=result["user"].full_name,
            role=result["user"].role.value,
            created_at=result["user"].created_at
        ),
        access_token=result["access_token"],
        refresh_token=result["refresh_token"]
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token

    Returns new access and refresh tokens.
    """
    service = AuthService(db)
    result = service.refresh_tokens(request.refresh_token)

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"]
    )


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking refresh token.

    Requires valid access token in Authorization header.

    - **refresh_token**: Refresh token to revoke

    Returns success message.
    """
    service = AuthService(db)
    service.logout(request.refresh_token)

    return {"message": "Logged out successfully"}
