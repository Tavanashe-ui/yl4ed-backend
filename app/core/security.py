# app/core/security.py
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext

# Security Configuration
# TODO: Move SECRET_KEY to your .env file before production
SECRET_KEY = "a_very_secret_and_long_random_string_for_yl4ed"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """Generates a JWT for authenticated users."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # We store the user's ID as the "sub" (subject) in the token
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if a provided password matches the database hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain text password before saving to the database."""
    return pwd_context.hash(password)