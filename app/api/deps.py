from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.core import security
from app.core.config import settings
from app.db.database import get_db
from app.db import models
from app.schemas.token import TokenPayload
from app.utils.audit import current_user_id, current_username

# This tells FastAPI where the frontend should send login requests to get the token
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(reusable_oauth2)
) -> models.User:
    """
    Validates the JWT token in the Authorization header.
    Returns the database User object if valid, otherwise throws an HTTP error.
    """
    try:
        # Decode the token using your secret key
        payload = jwt.decode(
            token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        if token_data.sub is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials - Subject missing",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
        
    # Query the database to ensure the user actually exists
    user = db.query(models.User).filter(models.User.id == int(token_data.sub)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # --- Audit: store user info in context variables for logging ---
    current_user_id.set(user.id)
    current_username.set(user.email)
    
    return user

def get_current_active_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Role-Based Access Control (RBAC): 
    Checks if the authenticated user has Admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="The user does not have enough privileges."
        )
    return current_user