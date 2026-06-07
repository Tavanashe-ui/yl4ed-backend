# app/schemas/executive.py
from pydantic import BaseModel, Field
from typing import Optional

from app.db.models import ExecutiveRoleEnum
from app.schemas.member import MemberOut 

class ExecutiveBase(BaseModel):
    role_category: ExecutiveRoleEnum
    position: str = Field(..., example="Provincial Chairperson")
    
    # Nullable because National executives might not have a specific province
    province_id: Optional[int] = None 

class ExecutiveCreate(ExecutiveBase):
    member_id: int

class ExecutiveUpdate(BaseModel):
    # All fields are optional so you can update just one thing at a time
    role_category: Optional[ExecutiveRoleEnum] = None
    position: Optional[str] = None
    province_id: Optional[int] = None

class ExecutiveOut(ExecutiveBase):
    id: int
    member_id: int
    
    # This nests the entire member profile
    member: MemberOut 

    class Config:
        from_attributes = True