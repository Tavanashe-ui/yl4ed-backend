from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.utils.audit import log_audit

from app.db.database import get_db
from app.db import models
from app.core import security
from app.core.config import settings
from app.utils.audit import log_audit

router = APIRouter()

@router.post("/login")
def login_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, getting an access token for future requests.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")

    # Case 1: User not found or password incorrect
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        log_audit(
            action="LOGIN_FAILED",
            username=form_data.username,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message="Invalid email or password"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Case 2: Account inactive
    if not user.is_active:
        log_audit(
            user_id=user.id,
            username=user.email,
            action="LOGIN_FAILED",
            ip_address=ip_address,
            user_agent=user_agent,
            error_message="Inactive user account"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Case 3: Successful login
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    log_audit(
        user_id=user.id,
        username=user.email,
        action="LOGIN",
        ip_address=ip_address,
        user_agent=user_agent,
        status_code=200
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "is_admin": user.is_admin
        }
    }