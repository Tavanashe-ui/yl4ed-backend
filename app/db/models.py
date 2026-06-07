# app/db/models.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

# --- Enums for strict choices ---
class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"

class ExecutiveRoleEnum(str, enum.Enum):
    NATIONAL = "National"
    PROVINCIAL = "Provincial"

# --- Tables ---

# app/db/models.py (Snippet)

class Province(Base):
    __tablename__ = "provinces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    # NEW: 2-character province code (e.g., 'HR' for Harare)
    code = Column(String(2), unique=True, index=True, nullable=False) 
    
    # Relationships
    districts = relationship("District", back_populates="province")
    members = relationship("Member", back_populates="province_rel")
    executives = relationship("Executive", back_populates="province_rel")
class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    province_id = Column(Integer, ForeignKey("provinces.id"), nullable=False)
    
    # Relationships
    province = relationship("Province", back_populates="districts")
    members = relationship("Member", back_populates="district_rel")

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    
    # PRD Requirement: Automatic Affiliation ID (e.g., YL4ED-2026-000001)
    affiliation_id = Column(String, unique=True, index=True, nullable=False) 
    
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    phone_number = Column(String, nullable=False)
    national_identity_number = Column(String, unique=True, nullable=False)
    email_address = Column(String, unique=True, nullable=True)
    residential_address = Column(Text, nullable=False)
    occupation = Column(String, nullable=True)
    place_of_birth = Column(String, nullable=False)
    
    # Relationships
    province_id = Column(Integer, ForeignKey("provinces.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    
    province_rel = relationship("Province", back_populates="members")
    district_rel = relationship("District", back_populates="members")
    executive_profile = relationship("Executive", back_populates="member", uselist=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Executive(Base):
    __tablename__ = "executives"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), unique=True, nullable=False)
    role_category = Column(Enum(ExecutiveRoleEnum), nullable=False)
    position = Column(String, nullable=False)
    
    # Nullable because National executives might not be tied to a specific province
    province_id = Column(Integer, ForeignKey("provinces.id"), nullable=True) 
    
    # Relationships
    member = relationship("Member", back_populates="executive_profile")
    province_rel = relationship("Province", back_populates="executives")

class User(Base):
    """Handles admin accounts for the dashboard login."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=True) # PRD Requirement: Role-based access control