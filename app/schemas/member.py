# app/schemas/member.py
from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime # Added datetime import
from typing import Optional
from app.db.models import GenderEnum

# --- Base Schema (Shared attributes) ---
class MemberBase(BaseModel):
    name: str = Field(..., min_length=2, example="John")
    surname: str = Field(..., min_length=2, example="Doe")
    date_of_birth: date
    gender: GenderEnum
    phone_number: str = Field(..., example="+263771234567")
    national_identity_number: str = Field(..., example="63-1234567X89")
    email_address: Optional[EmailStr] = None
    residential_address: str
    occupation: Optional[str] = None
    place_of_birth: str
    
    province_name: str  
    district_name: str

# --- Schema for Creating a Member (Input) ---
class MemberCreate(MemberBase):
    # Notice we do NOT include affiliation_id here. 
    # The frontend shouldn't send it; the backend generates it.
    pass

# --- Schema for Returning a Member (Output) ---
class MemberOut(MemberBase):
    id: int
    affiliation_id: str
    created_at: datetime # FIXED: Changed from date to datetime to cleanly map the Postgres timestamp

    # FIXED: Overriding inherited string fields to Optional so Pydantic doesn't crash 
    # when reading the core database object fields (which only natively hold relational keys)
    province_name: Optional[str] = None
    district_name: Optional[str] = None
    
    # Exposing the actual relational keys coming from the database
    province_id: int
    district_id: int

    class Config:
        from_attributes = True # Allows Pydantic to read SQLAlchemy models