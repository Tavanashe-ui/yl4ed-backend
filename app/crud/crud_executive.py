# app/crud/crud_executive.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db import models
from app.schemas import executive as schemas

def create_executive(db: Session, exec_in: schemas.ExecutiveCreate):
    """Promotes an existing member to an Executive role."""
    
    # 1. Ensure the member exists
    member = db.query(models.Member).filter(models.Member.id == exec_in.member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Cannot assign role: Member not found."
        )
    
    # 2. Ensure they aren't already an executive
    existing_exec = db.query(models.Executive).filter(models.Executive.member_id == exec_in.member_id).first()
    if existing_exec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="This member is already assigned to an executive position."
        )
        
    # 3. Validate Provincial logic
    if exec_in.role_category == models.ExecutiveRoleEnum.PROVINCIAL and not exec_in.province_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Provincial executives must be assigned a valid province_id."
        )

    # 4. Save to database
    db_exec = models.Executive(
        member_id=exec_in.member_id,
        role_category=exec_in.role_category,
        position=exec_in.position,
        province_id=exec_in.province_id
    )
    
    db.add(db_exec)
    db.commit()
    db.refresh(db_exec)
    return db_exec


def get_executives(db: Session, role: str = None, province_id: int = None):
    """
    Retrieves executives. Allows filtering by role (National/Provincial) 
    or by a specific province to group them on the dashboard.
    """
    query = db.query(models.Executive)
    
    if role:
        query = query.filter(models.Executive.role_category == role)
    if province_id:
        query = query.filter(models.Executive.province_id == province_id)
        
    return query.all()


def update_executive(db: Session, exec_id: int, exec_in: schemas.ExecutiveUpdate):
    """Updates an existing executive's position or role."""
    db_exec = db.query(models.Executive).filter(models.Executive.id == exec_id).first()
    if not db_exec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Executive not found."
        )

    update_data = exec_in.model_dump(exclude_unset=True)

    # Re-validate Provincial logic if role or province is being changed
    new_role = update_data.get("role_category", db_exec.role_category)
    new_province = update_data.get("province_id", db_exec.province_id)

    if new_role == models.ExecutiveRoleEnum.PROVINCIAL and not new_province:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Provincial executives must be assigned a valid province_id."
        )
        
    # Clean up province_id if changing from Provincial to National
    if new_role == models.ExecutiveRoleEnum.NATIONAL:
        update_data["province_id"] = None

    # Apply updates
    for field, value in update_data.items():
        setattr(db_exec, field, value)

    db.add(db_exec)
    db.commit()
    db.refresh(db_exec)
    return db_exec


def delete_executive(db: Session, exec_id: int):
    """Removes a member from their executive position (demotion)."""
    db_exec = db.query(models.Executive).filter(models.Executive.id == exec_id).first()
    if not db_exec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Executive not found."
        )
        
    db.delete(db_exec)
    db.commit()
    return {"detail": "Executive successfully removed."}