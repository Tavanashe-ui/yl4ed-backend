# app/api/v1/endpoints/stats.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from app.api import deps
from app.db.database import get_db
from app.db import models

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    # The dependency that locks this down to logged-in admins only
    current_user: models.User = Depends(deps.get_current_active_admin)
) -> Dict[str, Any]:
    """
    Retrieve full statistics for the YL4ED dashboard.
    """
    # 1. Total Registered Members
    total_members = db.query(models.Member).count()

    # 2. Members by Province (e.g., Harare, Bulawayo)
    # Uses an outer join so provinces with 0 members still show up
    provincial_stats = db.query(
        models.Province.name, 
        func.count(models.Member.id).label("count")
    ).outerjoin(models.Member).group_by(models.Province.name).all()

    # 3. Members by District (e.g., Mutare, Kwekwe)
    district_stats = db.query(
        models.District.name, 
        func.count(models.Member.id).label("count")
    ).outerjoin(models.Member).group_by(models.District.name).all()

    # 4. Gender Statistics
    gender_stats = db.query(
        models.Member.gender, 
        func.count(models.Member.id).label("count")
    ).group_by(models.Member.gender).all()

    # 5. Recent Registrations (Top 5 for the dashboard feed)
    recent_members = db.query(models.Member).order_by(
        models.Member.created_at.desc()
    ).limit(5).all()

    # Format the recent members into a clean dictionary
    recent_list = [
        {
            "affiliation_id": m.affiliation_id,
            "name": m.name,
            "surname": m.surname,
            "registered_on": m.created_at
        }
        for m in recent_members
    ]

    # Return the structured JSON response for the frontend charts
    return {
        "overview": {
            "total_members": total_members,
            "requested_by": current_user.email
        },
        "demographics": {
            "by_gender": {g[0].value if g[0] else "Unknown": g[1] for g in gender_stats},
        },
        "geography": {
            "by_province": {p[0]: p[1] for p in provincial_stats},
            "by_district": {d[0]: d[1] for d in district_stats}
        },
        "recent_registrations": recent_list
    }