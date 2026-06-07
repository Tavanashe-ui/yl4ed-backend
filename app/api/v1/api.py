# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import members, executives, auth, stats, files, provinces, districts, audit# Added files

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(members.router, prefix="/members", tags=["Members"])
api_router.include_router(executives.router, prefix="/executives", tags=["Executives"])
api_router.include_router(stats.router, prefix="/stats", tags=["Dashboard"])
api_router.include_router(files.router, prefix="/files", tags=["File Management"])
api_router.include_router(provinces.router, prefix="/provinces", tags=["Provinces"])
api_router.include_router(districts.router, prefix="/districts", tags=["Districts"])
api_router.include_router(audit.router, tags = ["audit"])