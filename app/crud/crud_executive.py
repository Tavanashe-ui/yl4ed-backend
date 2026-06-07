from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional

from app.db import models
from app.schemas import executive as schemas
from app.utils.audit import log_audit

def create_executive(
    db: Session,
    exec_in: schemas.ExecutiveCreate,
    user_id: Optional[int] = None,
    username: Optional[str] = None
):
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

    # Audit log
    log_audit(
        user_id=user_id,
        username=username,
        action="CREATE",
        resource_type="executive",
        resource_id=str(db_exec.id),
        new_data={
            "member_id": db_exec.member_id,
            "role_category": db_exec.role_category.value,
            "position": db_exec.position,
            "province_id": db_exec.province_id,
        },
        status_code=200,
    )
    return db_exec

def get_executives(db: Session, role: str = None, province_id: int = None):
    query = db.query(models.Executive)
    if role:
        query = query.filter(models.Executive.role_category == role)
    if province_id:
        query = query.filter(models.Executive.province_id == province_id)
    return query.all()

def update_executive(
    db: Session,
    exec_id: int,
    exec_in: schemas.ExecutiveUpdate,
    user_id: Optional[int] = None,
    username: Optional[str] = None
):
    db_exec = db.query(models.Executive).filter(models.Executive.id == exec_id).first()
    if not db_exec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Executive not found."
        )

    # Capture old data for audit
    old_data = {
        "role_category": db_exec.role_category.value,
        "position": db_exec.position,
        "province_id": db_exec.province_id,
    }

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

    # Audit log
    log_audit(
        user_id=user_id,
        username=username,
        action="UPDATE",
        resource_type="executive",
        resource_id=str(exec_id),
        old_data=old_data,
        new_data={
            "role_category": db_exec.role_category.value,
            "position": db_exec.position,
            "province_id": db_exec.province_id,
        },
        status_code=200,
    )
    return db_exec

def delete_executive(
    db: Session,
    exec_id: int,
    user_id: Optional[int] = None,
    username: Optional[str] = None
):
    db_exec = db.query(models.Executive).filter(models.Executive.id == exec_id).first()
    if not db_exec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Executive not found."
        )
    
    # Capture old data for audit
    old_data = {
        "member_id": db_exec.member_id,
        "role_category": db_exec.role_category.value,
        "position": db_exec.position,
    }
    
    db.delete(db_exec)
    db.commit()

    log_audit(
        user_id=user_id,
        username=username,
        action="DELETE",
        resource_type="executive",
        resource_id=str(exec_id),
        old_data=old_data,
        status_code=200,
    )
    return {"detail": "Executive successfully removed."}