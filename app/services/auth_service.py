"""Business logic service for user registration and authentication."""

from typing import Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest, UserLoginRequest
from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.config import settings


class AuthService:
    """Service handling credential validation, password hashing, and token issuance."""

    @staticmethod
    def register_user(db: Session, request: UserRegisterRequest) -> User:
        """Register a new user account.

        Guarantees that public registration assigns only the standard 'user' role
        and enforces email uniqueness.

        Raises:
            HTTPException(409): If an account with the requested email already exists.
        """
        try:
            existing_user = db.query(User).filter(User.email == request.email.lower().strip()).first()
        except SQLAlchemyError:
            db.rollback()
            raise

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{request.email}' already exists.",
            )

        hashed_pwd = hash_password(request.password)

        new_user = User(
            name=request.name.strip(),
            email=request.email.lower().strip(),
            password=hashed_pwd,
            role=UserRole.USER,  # Strictly force USER role
        )

        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{request.email}' already exists.",
            )
        except SQLAlchemyError:
            db.rollback()
            raise

    @staticmethod
    def authenticate_user(db: Session, request: UserLoginRequest) -> Tuple[User, str, int]:
        """Authenticate user credentials and issue an access token.

        Raises:
            HTTPException(401): If credentials are invalid.
        """
        try:
            user = db.query(User).filter(User.email == request.email.lower().strip()).first()
        except SQLAlchemyError:
            db.rollback()
            raise

        if not user or not verify_password(request.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_data = {
            "sub": str(user.id),
            "role": user.role.value,
        }
        access_token = create_access_token(token_data)
        expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return user, access_token, expires_in_seconds


auth_service = AuthService()
