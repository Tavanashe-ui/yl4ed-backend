from sqlalchemy.orm import Session
from sqlalchemy import exc, extract
from fastapi import HTTPException, status
from datetime import datetime
from typing import Optional

from app.db import models
from app.schemas import member as schemas
from app.utils.audit import log_audit

# Map your provinces to their codes
PROVINCE_CODES = {
    "Harare": "HR",
    "Bulawayo": "BY",
    "Manicaland": "MA",
    "Mashonaland Central": "MC",
    "Mashonaland East": "ME",
    "Mashonaland West": "MW",
    "Matabeleland North": "MN",
    "Matabeleland South": "MS",
    "Masvingo": "MV",
    "Midlands": "MI",
}

def get_member(db: Session, member_id: int):
    """Retrieve a single member by their primary key ID."""
    return db.query(models.Member).filter(models.Member.id == member_id).first()

def get_member_by_national_id(db: Session, national_id: str):
    """Check if a member already exists using their National Identity Number."""
    return db.query(models.Member).filter(models.Member.national_identity_number == national_id).first()

def get_members(db: Session, skip: int = 0, limit: int = 100):
    """Retrieve a paginated list of all members for the directory."""
    return db.query(models.Member).offset(skip).limit(limit).all()

def create_member(
    db: Session,
    member_in: schemas.MemberCreate,
    user_id: Optional[int] = None,
    username: Optional[str] = None
) -> models.Member:
    # 1. Match the Province by name (Case-Insensitive)
    province = db.query(models.Province).filter(
        models.Province.name.ilike(member_in.province_name)
    ).first()
    if not province:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Province '{member_in.province_name}' does not exist in the system."
        )

    # 2. Match the District by name (Case-Insensitive)
    district = db.query(models.District).filter(
        models.District.name.ilike(member_in.district_name)
    ).first()
    if not district:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"District '{member_in.district_name}' does not exist in the system."
        )

    # 3. Structural Validation
    if district.province_id != province.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"District '{member_in.district_name}' does not belong to the province '{member_in.province_name}'."
        )

    # 4. Check for duplicate National Registration Identity numbers
    duplicate = db.query(models.Member).filter(
        models.Member.national_identity_number == member_in.national_identity_number
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A member with this National Identity Number is already registered."
        )

    # 5. Extract fields and prepare for ID generation
    member_data = member_in.model_dump(exclude={"province_name", "district_name"})
    member_data["province_id"] = province.id
    member_data["district_id"] = district.id

    # 6. Generate Sequential Affiliation ID
    province_code = PROVINCE_CODES.get(province.name, "XX")
    current_year = datetime.now().year
    
    count = db.query(models.Member).filter(
        models.Member.province_id == province.id,
        extract('year', models.Member.created_at) == current_year
    ).count()
    
    sequence = str(count + 1).zfill(4)
    member_data["affiliation_id"] = f"YL4ED-{province_code}-{current_year}-{sequence}"

    # 7. Write to the database
    db_member = models.Member(**member_data)
    db.add(db_member)
    db.commit()
    db.refresh(db_member)

    # Audit log
    log_audit(
        user_id=user_id,
        username=username,
        action="CREATE",
        resource_type="member",
        resource_id=db_member.affiliation_id,
        new_data={
            "name": db_member.name,
            "surname": db_member.surname,
            "national_id": db_member.national_identity_number,
            "province": province.name,
            "district": district.name,
        },
        status_code=201,
    )
    return db_member

def delete_member(
    db: Session,
    member_id: int,
    user_id: Optional[int] = None,
    username: Optional[str] = None
) -> bool:
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if member:
        # Audit before deletion
        log_audit(
            user_id=user_id,
            username=username,
            action="DELETE",
            resource_type="member",
            resource_id=member.affiliation_id,
            old_data={
                "name": member.name,
                "surname": member.surname,
                "national_id": member.national_identity_number,
            },
            status_code=204,
        )
        db.delete(member)
        db.commit()
        return True
    return False