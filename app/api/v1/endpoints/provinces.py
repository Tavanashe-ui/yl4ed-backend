# app/api/v1/endpoints/provinces.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.api import deps
from app.schemas import province as schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.ProvinceOut])
def read_provinces(db: Session = Depends(get_db)):
    return db.query(models.Province).order_by(models.Province.name).all()

@router.post("/", response_model=schemas.ProvinceOut)
def create_province(
    province_in: schemas.ProvinceCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    existing = db.query(models.Province).filter(models.Province.name.ilike(province_in.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Province already exists.")
    db_province = models.Province(name=province_in.name)
    db.add(db_province)
    db.commit()
    db.refresh(db_province)
    return db_province

@router.get("/tree", response_model=List[schemas.ProvinceTreeOut])
def read_provinces_tree(db: Session = Depends(get_db)):
    """
    Returns all provinces along with their nested operational districts.
    Perfect for populating cross-linked dropdowns on the frontend in one single request.
    """
    return db.query(models.Province).order_by(models.Province.name).all()