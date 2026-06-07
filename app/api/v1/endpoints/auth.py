# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.database import get_db
from app.db import models
from app.core import security
from app.core.config import settings

router = APIRouter()

@router.post("/login")
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, getting an access token for future requests.
    """
    # 1. Look up the user by email
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # 2. Verify existence and password
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account"
        )

    # 4. Generate the JWT Token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "is_admin": user.is_admin
        }
    }