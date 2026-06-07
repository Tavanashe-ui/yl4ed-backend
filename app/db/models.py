# app/db/models.py
from app.utils.audit import log_audit
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import event, func
from sqlalchemy.orm import Session as SessionType
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

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL if system action or user deleted
    username = Column(String(100), nullable=True)  # Denormalised for quick search
    action = Column(String(50), nullable=False)    # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, IMPORT, VIEW
    resource_type = Column(String(50))             # "member", "user", "province", etc.
    resource_id = Column(String(100))              # e.g., member.id or affiliation_id
    endpoint = Column(String(255))                 # URL path
    method = Column(String(10))                    # GET, POST, PUT, DELETE
    ip_address = Column(String(45))                # IPv4/IPv6
    user_agent = Column(Text)
    old_data = Column(Text)                        # JSON string of previous state (for updates)
    new_data = Column(Text)                        # JSON string of new state (for creates/updates)
    status_code = Column(Integer)                  # HTTP response status
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

@event.listens_for(Member, 'after_insert')
def member_after_insert(mapper, connection, target):
    # We cannot easily get request context here, so we'll store minimal info
    # You can pass user_id via a global context variable (e.g., contextvars)
    log_audit(
        action="CREATE",
        resource_type="member",
        resource_id=target.affiliation_id or str(target.id),
        new_data={c.key: getattr(target, c.key) for c in target.__table__.columns if c.key not in ['id', 'created_at', 'updated_at']},
        # user_id and other request info are missing here – solve with contextvars (see below)
    )

@event.listens_for(Member, 'before_update')
def member_before_update(mapper, connection, target):
    # Capture old state from the database (requires a SELECT)
    # Use a separate connection to fetch old values
    pass

@event.listens_for(Member, 'before_delete')
def member_before_delete(mapper, connection, target):
    log_audit(
        action="DELETE",
        resource_type="member",
        resource_id=target.affiliation_id or str(target.id),
        old_data={c.key: getattr(target, c.key) for c in target.__table__.columns},
    )
