"""Password hashing and verification utilities using bcrypt.

Provides industry-standard salted hashing and timing-safe verification.
Compatible with Python 3.12+ without passlib version conflicts.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt with a work factor of 12.

    Args:
        password: Raw plain text password.

    Returns:
        UTF-8 encoded string containing algorithm, cost, salt, and hash.
    """
    # Truncate to 72 bytes if necessary per bcrypt specification
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plain text password matches a stored bcrypt hash.

    Args:
        plain_password: Raw plain text candidate password.
        hashed_password: Stored bcrypt hash string.

    Returns:
        True if credentials match, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except (ValueError, TypeError):
        return False
