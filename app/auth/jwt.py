"""JWT creation, signing, and verification utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError
from app.config import settings


class JWTError(Exception):
    """Base exception for JWT processing failures."""
    pass


class TokenExpiredError(JWTError):
    """Raised when token expiration timestamp has passed."""
    pass


class TokenInvalidError(JWTError):
    """Raised when token signature or format is invalid."""
    pass


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate and sign a JWT access token.

    Args:
        data: Claims dictionary (must include 'sub' and optionally 'role').
        expires_delta: Optional custom duration override.

    Returns:
        Encoded and signed JWT string.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    })

    # Ensure subject is string formatted
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token.

    Args:
        token: Raw JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        TokenExpiredError: If token has expired.
        TokenInvalidError: If token signature or structure is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token signature has expired") from exc
    except (InvalidTokenError, PyJWTError) as exc:
        raise TokenInvalidError("Invalid token signature or format") from exc
