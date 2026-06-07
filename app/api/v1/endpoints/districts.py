# app/api/v1/endpoints/districts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.db import models
from app.schemas import district as schemas
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[schemas.DistrictOut])
def read_districts(province_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.District)
    if province_id:
        query = query.filter(models.District.province_id == province_id)
    return query.order_by(models.District.name).all()

@router.post("/", response_model=schemas.DistrictOut)
def create_district(
    district_in: schemas.DistrictCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    existing = db.query(models.District).filter(
        models.District.name.ilike(district_in.name),
        models.District.province_id == district_in.province_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="District already exists in this province.")
    db_district = models.District(name=district_in.name, province_id=district_in.province_id)
    db.add(db_district)
    db.commit()
    db.refresh(db_district)
    return db_district