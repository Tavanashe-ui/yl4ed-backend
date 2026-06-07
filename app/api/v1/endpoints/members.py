from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas import member as schemas
from app.crud import crud_member
from app.api import deps
from app.db import models

router = APIRouter()

@router.post("/", response_model=schemas.MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(
    member_in: schemas.MemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Register a new member. Catches duplication errors for email/national ID.
    """
    db_member = crud_member.get_member_by_national_id(db, national_id=member_in.national_identity_number)
    if db_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A member with this National Identity Number already exists."
        )
    
    try:
        return crud_member.create_member(
            db,
            member_in,
            user_id=current_user.id,
            username=current_user.email
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this email address or identifier already exists."
        )

@router.get("/", response_model=List[schemas.MemberOut])
def read_members(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Retrieve all members for the directory dashboard.
    """
    members = crud_member.get_members(db, skip=skip, limit=limit)
    return members

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Remove a member from the directory.
    """
    success = crud_member.delete_member(
        db,
        member_id,
        user_id=current_user.id,
        username=current_user.email
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found."
        )
    return None