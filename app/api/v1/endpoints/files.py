# app/api/v1/endpoints/files.py
"""
Bulk Import & Export endpoints for YL4ED Membership Management System.

Routes:
  POST /files/import            – Upload an Excel file, parse rows, insert valid members
  GET  /files/export            – Export members as branded PDF (filterable)
  GET  /files/import/template   – Download blank import template (.xlsx)
  POST /files/import/preview    – Parse an Excel file and return preview without inserting
"""
import io
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.db.database import get_db
from app.db import models
from app.core import pdf_utils
from app.core import excel_utils
from app.crud import crud_member
from app.schemas import member as schemas

router = APIRouter()

EXCEL_EXTENSIONS = (".xlsx", ".xls")
EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def _is_excel(filename: str) -> bool:
    return filename.lower().endswith(EXCEL_EXTENSIONS)


def _pdf_stream(buffer: io.BytesIO, filename: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _excel_stream(buffer: io.BytesIO, filename: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─────────────────────────────────────────────────────────────
#  GET /files/import/template
# ─────────────────────────────────────────────────────────────
@router.get("/import/template", summary="Download blank bulk-import template (.xlsx)")
def download_import_template(
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Returns a formatted .xlsx workbook with the correct column headers,
    50 blank rows, gender dropdown, and an Instructions sheet.
    """
    buffer = excel_utils.generate_import_template_excel()
    return _excel_stream(buffer, "yl4ed_import_template.xlsx")


# ─────────────────────────────────────────────────────────────
#  POST /files/import/preview
# ─────────────────────────────────────────────────────────────
@router.post("/import/preview", summary="Preview parsed rows from an Excel file without importing")
async def preview_import(
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Parse an Excel file and return a summary of valid rows and validation errors
    without writing anything to the database.
    """
    if not _is_excel(file.filename or ""):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    result = excel_utils.parse_uploaded_excel(file_bytes)
    return {
        "filename":      file.filename,
        "total_found":   result["total_found"],
        "valid_count":   result["valid_count"],
        "error_count":   result["error_count"],
        "valid_records": result["records"][:5],
        "errors":        result["errors"][:10],
    }


# ─────────────────────────────────────────────────────────────
#  POST /files/import
# ─────────────────────────────────────────────────────────────
@router.post("/import", summary="Bulk import members from an Excel file")
async def bulk_import_members(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Upload an Excel file (.xlsx/.xls) containing member records.
    Valid rows are inserted; duplicate National IDs are skipped with a note.
    """
    if not _is_excel(file.filename or ""):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    result = excel_utils.parse_uploaded_excel(file_bytes)
    if result["total_found"] == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "No recognisable member data found. "
                "Ensure your Excel file has the correct column headers in row 1. "
                "Download the template from /files/import/template."
            )
        )

    inserted:  list[dict] = []
    skipped:   list[dict] = []
    db_errors: list[dict] = []

    for row in result["records"]:
        existing = crud_member.get_member_by_national_id(
            db, national_id=row.get("national_identity_number", "")
        )
        if existing:
            skipped.append({
                "national_identity_number": row.get("national_identity_number"),
                "reason": "Duplicate National Identity Number – already registered."
            })
            continue

        try:
            member_in = schemas.MemberCreate(**row)
            new_member = crud_member.create_member(db, member_in)
            inserted.append({
                "affiliation_id": new_member.affiliation_id,
                "name": new_member.name,
                "surname": new_member.surname,
            })
        except HTTPException as exc:
            db_errors.append({
                "national_identity_number": row.get("national_identity_number"),
                "reason": exc.detail,
            })
        except Exception as exc:
            db.rollback()
            db_errors.append({
                "national_identity_number": row.get("national_identity_number"),
                "reason": str(exc),
            })

    return {
        "filename":            file.filename,
        "total_found":         result["total_found"],
        "parse_errors":        result["error_count"],
        "inserted":            len(inserted),
        "skipped":             len(skipped),
        "db_errors":           len(db_errors),
        "inserted_records":    inserted,
        "skipped_records":     skipped,
        "db_error_records":    db_errors,
        "parse_error_details": result["errors"][:20],
    }


# ─────────────────────────────────────────────────────────────
#  GET /files/export  (unchanged — still exports as PDF)
# ─────────────────────────────────────────────────────────────
@router.get("/export", summary="Export member directory as PDF")
def export_members_pdf(
    province_id: Optional[int]               = Query(None, description="Filter by province ID"),
    district_id: Optional[int]               = Query(None, description="Filter by district ID"),
    gender:      Optional[models.GenderEnum] = Query(None, description="Filter by gender (M or F)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_admin)
):
    """
    Generate and stream a branded landscape A4 PDF of the member directory.
    Supports optional filtering by province, district, and gender.
    """
    query = db.query(models.Member)

    province_name = None
    district_name = None

    if province_id:
        province = db.query(models.Province).filter(models.Province.id == province_id).first()
        if not province:
            raise HTTPException(status_code=404, detail="Province not found.")
        query = query.filter(models.Member.province_id == province_id)
        province_name = province.name

    if district_id:
        district = db.query(models.District).filter(models.District.id == district_id).first()
        if not district:
            raise HTTPException(status_code=404, detail="District not found.")
        query = query.filter(models.Member.district_id == district_id)
        district_name = district.name

    if gender:
        query = query.filter(models.Member.gender == gender)

    members = query.order_by(models.Member.affiliation_id).all()

    if not members:
        raise HTTPException(
            status_code=404,
            detail="No members found matching the specified filters."
        )

    parts = ["yl4ed_members"]
    if province_name:
        parts.append(province_name.replace(" ", "_").lower())
    if district_name:
        parts.append(district_name.replace(" ", "_").lower())
    if gender:
        parts.append(gender.value.lower())
    filename = "_".join(parts) + ".pdf"

    pdf_buffer = pdf_utils.generate_members_pdf(
        members,
        province_name=province_name,
        district_name=district_name,
        gender_filter=gender.value if gender else None,
    )

    return _pdf_stream(pdf_buffer, filename)
