# app/core/pdf_utils.py
"""
PDF utilities for YL4ED Membership Management System.
  - parse_uploaded_pdf : Extract member rows from a structured PDF (table or text layout)
  - generate_members_pdf : Export styled member directory PDF
  - generate_import_template_pdf : Generate a blank template for bulk import
"""
import io
import re
import pdfplumber
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas as rl_canvas

from app.db import models

# ──────────────────────────────────────────────
# BRAND COLOURS
# ──────────────────────────────────────────────
NAVY      = colors.HexColor('#003580')
GOLD      = colors.HexColor('#C9A84C')
LIGHT_BLU = colors.HexColor('#E8F0FE')
MID_GREY  = colors.HexColor('#6B7280')
LIGHT_GRY = colors.HexColor('#F9FAFB')

# ──────────────────────────────────────────────
# COLUMN ALIASES  (what different upload PDFs may call each field)
# ──────────────────────────────────────────────
COLUMN_ALIASES: Dict[str, List[str]] = {
    "name":                     ["name", "first name", "firstname", "given name"],
    "surname":                  ["surname", "last name", "lastname", "family name"],
    "date_of_birth":            ["date of birth", "dob", "birth date", "birthdate"],
    "gender":                   ["gender", "sex"],
    "phone_number":             ["phone", "phone number", "mobile", "contact number", "cell"],
    "national_identity_number": ["national id", "national identity number", "id number",
                                 "national id number", "id no", "nin"],
    "email_address":            ["email", "email address", "e-mail"],
    "residential_address":      ["address", "residential address", "home address"],
    "occupation":               ["occupation", "job", "profession", "work"],
    "place_of_birth":           ["place of birth", "birth place", "birthplace", "pob"],
    "province_name":            ["province", "province name"],
    "district_name":            ["district", "district name", "current district"],
}

def _normalise_col(raw: str) -> str:
    """Lower-case and strip a column header for matching."""
    return (raw or "").strip().lower()

def _map_headers(headers: List[str]) -> Dict[int, str]:
    """Return {column_index: canonical_field_name} for recognised headers."""
    mapping: Dict[int, str] = {}
    for idx, raw_header in enumerate(headers):
        norm = _normalise_col(raw_header)
        for field, aliases in COLUMN_ALIASES.items():
            if norm in aliases:
                mapping[idx] = field
                break
    return mapping


# ──────────────────────────────────────────────
# IMPORT: PARSE UPLOADED PDF
# ──────────────────────────────────────────────
def parse_uploaded_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parse a bulk-import PDF.

    Returns:
        {
          "records":  [ {field: value, ...}, ... ],   # successfully parsed rows
          "errors":   [ {"row": int, "issues": [str]}, ... ],  # rows with problems
          "total_found": int,
          "valid_count": int,
          "error_count": int,
        }
    """
    records: List[Dict[str, str]] = []
    errors:  List[Dict[str, Any]] = []

    REQUIRED = [
        "name", "surname", "date_of_birth", "gender",
        "phone_number", "national_identity_number",
        "residential_address", "place_of_birth",
        "province_name", "district_name",
    ]

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()

            if tables:
                # ── Table-based PDF ──
                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    # First row = headers
                    raw_headers = [str(h) if h else "" for h in table[0]]
                    col_map = _map_headers(raw_headers)

                    if len(col_map) < 4:
                        # Not enough recognised columns – skip this table
                        continue

                    for row_idx, row in enumerate(table[1:], start=2):
                        row_data: Dict[str, str] = {}
                        for col_idx, field_name in col_map.items():
                            cell = row[col_idx] if col_idx < len(row) else None
                            row_data[field_name] = (cell or "").strip()

                        issues = _validate_row(row_data, REQUIRED)
                        global_row = (page_num - 1) * 1000 + row_idx  # rough row number

                        if issues:
                            errors.append({"row": global_row, "data": row_data, "issues": issues})
                        else:
                            records.append(_clean_row(row_data))
            else:
                # ── Text-based PDF fallback (key: value layout) ──
                text = page.extract_text() or ""
                parsed = _parse_text_block(text)
                if parsed:
                    issues = _validate_row(parsed, REQUIRED)
                    if issues:
                        errors.append({"row": page_num, "data": parsed, "issues": issues})
                    else:
                        records.append(_clean_row(parsed))

    return {
        "records":     records,
        "errors":      errors,
        "total_found": len(records) + len(errors),
        "valid_count": len(records),
        "error_count": len(errors),
    }


def _validate_row(data: Dict[str, str], required: List[str]) -> List[str]:
    issues = []
    for field in required:
        if not data.get(field, "").strip():
            issues.append(f"Missing required field: '{field}'")

    # Gender normalisation check
    gender_raw = data.get("gender", "").strip().upper()
    if gender_raw and gender_raw not in ("M", "F", "MALE", "FEMALE"):
        issues.append(f"Invalid gender value: '{data.get('gender')}' (expected M or F)")

    # Date of birth format check
    dob = data.get("date_of_birth", "").strip()
    if dob:
        parsed_dob = _parse_date(dob)
        if not parsed_dob:
            issues.append(f"Unrecognised date format for date_of_birth: '{dob}'")

    return issues


def _clean_row(data: Dict[str, str]) -> Dict[str, str]:
    """Normalise values before insertion."""
    cleaned = dict(data)
    # Normalise gender
    g = cleaned.get("gender", "").strip().upper()
    cleaned["gender"] = "M" if g in ("M", "MALE") else "F" if g in ("F", "FEMALE") else g
    # Normalise date
    dob = cleaned.get("date_of_birth", "")
    parsed = _parse_date(dob)
    if parsed:
        cleaned["date_of_birth"] = parsed
    return cleaned


def _parse_date(raw: str) -> Optional[str]:
    """Try multiple date formats, return YYYY-MM-DD or None."""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y",
                "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_text_block(text: str) -> Dict[str, str]:
    """
    Attempt to extract key:value pairs from free-text PDF pages.
    Supports lines like  "Name: John"  or  "NAME : John".
    """
    data: Dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key_raw, _, val = line.partition(":")
        norm_key = _normalise_col(key_raw.strip())
        val = val.strip()
        for field, aliases in COLUMN_ALIASES.items():
            if norm_key in aliases:
                data[field] = val
                break
    return data


# ──────────────────────────────────────────────
# EXPORT: GENERATE MEMBERS PDF
# ──────────────────────────────────────────────
def _page_footer(canvas, doc, total: int, filter_desc: str):
    """Draw footer on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_GREY)
    canvas.drawString(15*mm, 8*mm,
        f"YL4ED Membership Management System  ·  Total records: {total}  ·  {filter_desc}")
    canvas.drawRightString(A4[0] - 15*mm, 8*mm,
        f"Page {doc.page}  ·  Generated {datetime.now().strftime('%d %b %Y %H:%M')}")
    canvas.restoreState()


def generate_members_pdf(
    members: List[models.Member],
    province_name: Optional[str] = None,
    district_name: Optional[str] = None,
    gender_filter: Optional[str] = None,
) -> io.BytesIO:
    """
    Generate a polished, branded A4 member directory PDF.
    Supports optional filter description in the footer.
    """
    buffer = io.BytesIO()

    # Build filter description string
    filter_parts = []
    if province_name:
        filter_parts.append(f"Province: {province_name}")
    if district_name:
        filter_parts.append(f"District: {district_name}")
    if gender_filter:
        filter_parts.append(f"Gender: {gender_filter}")
    filter_desc = " | ".join(filter_parts) if filter_parts else "All Members"

    total = len(members)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=18*mm, bottomMargin=18*mm,
        leftMargin=12*mm, rightMargin=12*mm,
        onFirstPage=lambda c, d: _page_footer(c, d, total, filter_desc),
        onLaterPages=lambda c, d: _page_footer(c, d, total, filter_desc),
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('YLTitle', parent=styles['Normal'],
        fontSize=20, fontName='Helvetica-Bold', textColor=NAVY,
        alignment=TA_CENTER, spaceAfter=1*mm)
    sub_style = ParagraphStyle('YLSub', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica', textColor=MID_GREY,
        alignment=TA_CENTER, spaceAfter=5*mm)
    filter_style = ParagraphStyle('YLFilter', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica-Oblique', textColor=MID_GREY,
        alignment=TA_CENTER, spaceAfter=4*mm)
    stat_style = ParagraphStyle('YLStat', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica', textColor=NAVY,
        alignment=TA_RIGHT, spaceAfter=3*mm)

    story = []

    # ── Header ──
    story.append(Paragraph("YL4ED · Member Directory Export", title_style))
    story.append(Paragraph(
        "Young Leaders for Economic Development — Membership Management System",
        sub_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=3*mm))

    if filter_parts:
        story.append(Paragraph(f"Filtered by: {filter_desc}", filter_style))

    male_count   = sum(1 for m in members if m.gender and m.gender.value == "M")
    female_count = sum(1 for m in members if m.gender and m.gender.value == "F")
    story.append(Paragraph(
        f"Records: <b>{total}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Male: <b>{male_count}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Female: <b>{female_count}</b>",
        stat_style
    ))

    # ── Table ──
    headers = [
        'Affiliation ID', 'Name', 'Surname', 'Nat. ID',
        'Gender', 'DOB', 'Phone', 'Email',
        'Province', 'District', 'Occupation'
    ]

    col_widths = [
        38*mm, 28*mm, 28*mm, 30*mm,
        14*mm, 22*mm, 26*mm, 42*mm,
        26*mm, 26*mm, 28*mm
    ]

    table_data = [headers]
    for m in members:
        dob_str = m.date_of_birth.strftime("%d/%m/%Y") if m.date_of_birth else ""
        table_data.append([
            m.affiliation_id or "",
            m.name or "",
            m.surname or "",
            m.national_identity_number or "",
            m.gender.value if m.gender else "",
            dob_str,
            m.phone_number or "",
            m.email_address or "",
            m.province_rel.name if m.province_rel else "",
            m.district_rel.name if m.district_rel else "",
            m.occupation or "",
        ])

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',   (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR',    (0, 0), (-1, 0), colors.white),
        ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, 0), 8),
        ('ALIGN',        (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING',   (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING',(0, 0), (-1, 0), 5),
        # Data rows
        ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',     (0, 1), (-1, -1), 7.5),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, LIGHT_BLU]),
        ('ALIGN',        (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',   (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 1), (-1, -1), 3),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        # Grid
        ('GRID',         (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
        ('LINEBELOW',    (0, 0), (-1, 0), 1.5, GOLD),
    ]))

    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer


# ──────────────────────────────────────────────
# EXPORT: GENERATE BLANK IMPORT TEMPLATE PDF
# ──────────────────────────────────────────────
def generate_import_template_pdf() -> io.BytesIO:
    """
    Generate a blank, printer-friendly import template PDF with
    column headers matching the expected bulk-import format.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=15*mm, bottomMargin=15*mm,
        leftMargin=12*mm, rightMargin=12*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TTitle', parent=styles['Normal'],
        fontSize=16, fontName='Helvetica-Bold', textColor=NAVY,
        alignment=TA_CENTER, spaceAfter=2*mm)
    sub_style = ParagraphStyle('TSub', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica', textColor=MID_GREY,
        alignment=TA_CENTER, spaceAfter=5*mm)
    note_style = ParagraphStyle('TNote', parent=styles['Normal'],
        fontSize=7.5, fontName='Helvetica-Oblique', textColor=MID_GREY,
        spaceAfter=3*mm)

    story = []
    story.append(Paragraph("YL4ED · Bulk Member Import Template", title_style))
    story.append(Paragraph(
        "Complete all required (*) fields. Date format: YYYY-MM-DD. Gender: M or F. "
        "Upload this PDF via the Bulk Import panel on the Members page.",
        sub_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=4*mm))

    headers = [
        'Name *', 'Surname *', 'Date of Birth *\n(YYYY-MM-DD)',
        'Gender *\n(M/F)', 'Phone Number *', 'National ID *',
        'Email', 'Address *', 'Place of Birth *',
        'Province *', 'District *', 'Occupation'
    ]

    col_widths = [22*mm, 22*mm, 25*mm, 16*mm, 25*mm, 28*mm,
                  32*mm, 34*mm, 24*mm, 24*mm, 22*mm, 22*mm]

    # 20 blank rows
    rows = [[''] * len(headers) for _ in range(20)]
    table_data = [headers] + rows

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 7),
        ('ALIGN',         (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('LINEBELOW',     (0, 0), (-1, 0), 1.5, GOLD),
        # Data rows
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, LIGHT_GRY]),
        ('ROWHEIGHTS',    (0, 1), (-1, -1), 10*mm),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "* Required fields must not be left blank. Province and District must match names registered in the system exactly.",
        note_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
