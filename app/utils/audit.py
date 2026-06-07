import json
from contextvars import ContextVar
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db import models

# Context variables to hold request-scoped data (set by middleware or dependency)
current_user_id: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)
current_username: ContextVar[Optional[str]] = ContextVar('current_username', default=None)
current_ip: ContextVar[Optional[str]] = ContextVar('current_ip', default=None)
current_user_agent: ContextVar[Optional[str]] = ContextVar('current_user_agent', default=None)

def log_audit(
    *,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
    status_code: Optional[int] = None,
    error_message: Optional[str] = None,
):
    """Insert an audit log entry using a separate database session."""
    db = SessionLocal()
    try:
        audit = models.AuditLog(
            user_id=user_id or current_user_id.get(),
            username=username or current_username.get(),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address or current_ip.get(),
            user_agent=user_agent or current_user_agent.get(),
            old_data=json.dumps(old_data) if old_data else None,
            new_data=json.dumps(new_data) if new_data else None,
            status_code=status_code,
            error_message=error_message,
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()