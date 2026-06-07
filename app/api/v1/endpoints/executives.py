# app/api/v1/endpoints/executives.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api import deps
from app.db.database import get_db
from app.db import models
from app.schemas import executive as schemas
from app.crud import crud_executive

router = APIRouter()

@router.post("/", response_model=schemas.ExecutiveOut)
def assign_executive(
    exec_in: schemas.ExecutiveCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Assign an existing member to a National or Provincial Executive position.
    """
    return crud_executive.create_executive(db, exec_in)


@router.get("/", response_model=List[schemas.ExecutiveOut])
def read_executives(
    role: Optional[models.ExecutiveRoleEnum] = None,
    province_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Retrieve the executive directory. 
    Pass query parameters (?role=Provincial&province_id=3) to filter.
    """
    return crud_executive.get_executives(db, role=role, province_id=province_id)


@router.patch("/{exec_id}", response_model=schemas.ExecutiveOut)
def update_executive(
    exec_id: int,
    exec_in: schemas.ExecutiveUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Update an executive's position, role category, or assigned province.
    """
    return crud_executive.update_executive(db, exec_id=exec_id, exec_in=exec_in)


@router.delete("/{exec_id}", status_code=200)
def remove_executive(
    exec_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Remove an executive assignment from a member (demotion).
    The underlying member profile remains intact.
    """
    return crud_executive.delete_executive(db, exec_id=exec_id)