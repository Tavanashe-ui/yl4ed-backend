# app/api/v1/endpoints/members.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app.db.database import get_db
from app.schemas import member as schemas
from app.crud import crud_member

router = APIRouter()

@router.post("/", response_model=schemas.MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(
    member_in: schemas.MemberCreate, 
    db: Session = Depends(get_db)
):
    """
    Register a new member. Catches duplication errors for email/national ID.
    """
    # 1. Manual Check for National ID
    db_member = crud_member.get_member_by_national_id(db, national_id=member_in.national_identity_number)
    if db_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A member with this National Identity Number already exists."
        )
    
    # 2. Try to create with database integrity protection
    try:
        return crud_member.create_member(db, member_in)
    except IntegrityError:
        db.rollback() # Rollback the failed transaction
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this email address or identifier already exists in our records."
        )

@router.get("/", response_model=List[schemas.MemberOut])
def read_members(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Retrieve all members for the directory dashboard.
    """
    members = crud_member.get_members(db, skip=skip, limit=limit)
    return members

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """
    Remove a member from the directory.
    """
    success = crud_member.delete_member(db, member_id=member_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found."
        )
    return None