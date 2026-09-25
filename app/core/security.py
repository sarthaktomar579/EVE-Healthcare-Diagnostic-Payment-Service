from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generates bcrypt hash from plain password"""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    role: str = "PATIENT",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a signed JWT access token with user claims and expiration"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT token"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
