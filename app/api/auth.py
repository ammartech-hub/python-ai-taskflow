"""Authentication API routes for user registration, login, and profile retrieval."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.schemas.user import UserRegisterRequest, UserLoginRequest, UserResponse
from app.schemas.token import Token
from app.services.auth_service import auth_service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Registers a standard user account. Requires name, valid email, and minimum 8-character password. "
        "Public registration always defaults to the 'user' role. Rejects duplicate emails with HTTP 409."
    ),
)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user and return safe user profile."""
    user = auth_service.register_user(db, request)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and receive JWT",
    description=(
        "Validates email and password credentials. Returns an access JWT Bearer token upon success. "
        "Returns HTTP 401 for invalid credentials."
    ),
)
def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Validate user credentials and return signed access token."""
    user, access_token, expires_in = auth_service.authenticate_user(db, request)
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user profile",
    description="Returns the safe profile of the currently authenticated user based on the Bearer JWT.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return authenticated caller's profile without credential hashes."""
    return UserResponse.model_validate(current_user)
