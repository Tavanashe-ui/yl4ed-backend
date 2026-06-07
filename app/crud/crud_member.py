# app/crud/crud_member.py
from sqlalchemy.orm import Session
from sqlalchemy import exc, extract
from fastapi import HTTPException, status
from datetime import datetime

from app.db import models
from app.schemas import member as schemas

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

def create_member(db: Session, member_in: schemas.MemberCreate) -> models.Member:
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
    # Format: YL4ED-[PROVINCE CODE]-[YEAR]-[SEQUENTIAL]
    province_code = PROVINCE_CODES.get(province.name, "XX")
    current_year = datetime.now().year
    
    # Count existing members for this specific province in this specific year
    count = db.query(models.Member).filter(
        models.Member.province_id == province.id,
        extract('year', models.Member.created_at) == current_year
    ).count()
    
    # Generate the formatted string with 4-digit padding
    sequence = str(count + 1).zfill(4)
    member_data["affiliation_id"] = f"YL4ED-{province_code}-{current_year}-{sequence}"

    # 7. Write to the database
    db_member = models.Member(**member_data)
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    
    return db_member

def delete_member(db: Session, member_id: int):
    """Delete a member by their primary key ID."""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if member:
        db.delete(member)
        db.commit()
        return True
    return False