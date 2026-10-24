"""
Handles reading, validating and upserting attendance Excel files.

Expected columns (case-insensitive, flexible spacing/underscore):
    Emp No, Employee Name, Date, Attendance Status, CheckIn, CheckOut, Comments

Rules implemented here satisfy the core requirements:
  * emp_id is the unique key for Employees -> INSERT only if new, never duplicated.
  * (emp_id, date) is unique for Attendance -> INSERT if new, UPDATE if it
    already exists. Full history across dates is preserved (we never delete
    or overwrite other dates).
  * Bad rows (missing emp id, invalid date, invalid status, bad time format)
    are collected as errors and skipped, without failing the whole upload.
"""
import io
import re
from datetime import datetime, date as date_cls, time as time_cls

import pandas as pd
from sqlalchemy.orm import Session

from . import models

VALID_STATUSES = {
    "present": "Present",
    "p": "Present",

    "absent": "Absent",
    "a": "Absent",

    "wfh": "WFH",
    "work from home": "WFH",
    "work-from-home": "WFH",

    "leave": "Leave",
    "l": "Leave",
    "on leave": "Leave",

    "half day": "Half Day",
    "half-day": "Half Day",
    "halfday": "Half Day",
    "hd": "Half Day",
    
    "sick leave": "Sick leave",
    "sick": "Sick leave",
    "public holiday": "Public Holiday",
    "public": "Public Holiday",
    "weekly holiday": "Weekly Holiday",
    "week off": "Weekly Holiday",
    
    
}

# Map many possible header spellings to a canonical internal name
COLUMN_ALIASES = {
    "emp_id": ["emp no", "empno", "emp_no", "emp id", "empid", "emp_id", "employee no", "employee id", "employee_id"],
    "name": ["employee name", "name", "emp name", "empname", "employee_name"],
    "date": ["date", "attendance date", "att date"],
    "status": ["attendance status", "status", "attendance"],
    "check_in": ["checkin", "check in", "check_in", "in time", "intime"],
    "check_out": ["checkout", "check out", "check_out", "out time", "outtime"],
    "comments": ["comments", "comment", "remarks", "notes"],
}


def _normalize_header(h: str) -> str:
    return re.sub(r"\s+", " ", str(h).strip().lower())


def _map_columns(df: pd.DataFrame) -> dict:
    """Return {canonical_name: actual_dataframe_column} or raise ValueError."""
    normalized = {_normalize_header(c): c for c in df.columns}
    mapping = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            if alias in normalized:
                found = normalized[alias]
                break
        mapping[canonical] = found

    missing_required = [
        k for k in ("emp_id", "name", "date", "status") if mapping[k] is None
    ]
    if missing_required:
        raise ValueError(
            "Missing required column(s): "
            + ", ".join(missing_required)
            + ". Expected headers like: Emp No, Employee Name, Date, Attendance Status, CheckIn, CheckOut, Comments."
        )
    return mapping


def _parse_date(val):
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date_cls):
        return val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


def _parse_time(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, time_cls):
        return val
    if isinstance(val, datetime):
        return val.time()
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "nat", "none", "-"):
        return None
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    try:
        return pd.to_datetime(s).time()
    except Exception:
        return None


def _parse_status(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    key = str(val).strip().lower()
    return VALID_STATUSES.get(key)


def process_excel_file(db: Session, filename: str, file_bytes: bytes) -> models.UploadLog:
    """
    Parses the uploaded Excel file, validates each row, and upserts
    Employees + Attendance records. Returns a populated UploadLog
    (not yet committed by caller -- this function commits internally).
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"Could not read Excel file: {exc}")

    if df.empty:
        raise ValueError("The uploaded file contains no data rows.")

    col_map = _map_columns(df)

    total_rows = len(df)
    new_employees = 0
    inserted_attendance = 0
    updated_attendance = 0
    errors = []
    preview_inserted = []
    preview_updated = []

    # Cache existing employees & attendance keys for fast lookups within this batch
    existing_emp_ids = {e.emp_id for e in db.query(models.Employee.emp_id).all()}
    existing_att_keys = {
        (a.emp_id, a.date) for a in db.query(models.Attendance.emp_id, models.Attendance.date).all()
    }

    for idx, row in df.iterrows():
        excel_row_no = idx + 2  # +1 for 0-index, +1 for header row
        try:
            raw_emp_id = row.get(col_map["emp_id"])
            raw_name = row.get(col_map["name"])
            raw_date = row.get(col_map["date"])
            raw_status = row.get(col_map["status"])
            raw_checkin = row.get(col_map["check_in"]) if col_map["check_in"] else None
            raw_checkout = row.get(col_map["check_out"]) if col_map["check_out"] else None
            raw_comments = row.get(col_map["comments"]) if col_map["comments"] else None

            if pd.isna(raw_emp_id) or str(raw_emp_id).strip() == "":
                errors.append({"row": excel_row_no, "reason": "Missing Emp No", "data": None})
                continue
            emp_id = str(raw_emp_id).strip()
            # normalize things like 101.0 -> "101" when Excel stores as float
            if emp_id.endswith(".0"):
                emp_id = emp_id[:-2]

            if pd.isna(raw_name) or str(raw_name).strip() == "":
                errors.append({"row": excel_row_no, "reason": f"Missing Employee Name for {emp_id}", "data": None})
                continue
            name = str(raw_name).strip()

            att_date = _parse_date(raw_date)
            if att_date is None:
                errors.append({"row": excel_row_no, "reason": f"Invalid/missing Date for {emp_id}", "data": None})
                continue

            status = _parse_status(raw_status)
            if status is None:
                errors.append(
                    {
                        "row": excel_row_no,
                        "reason": f"Invalid Attendance Status '{raw_status}' for {emp_id} (expected Present/Absent/WFH/Leave/Half Day)",
                        "data": None,
                    }
                )
                continue

            check_in = _parse_time(raw_checkin)
            check_out = _parse_time(raw_checkout)
            comments = None if raw_comments is None or (isinstance(raw_comments, float) and pd.isna(raw_comments)) else str(raw_comments).strip()

            # --- Upsert Employee (emp_id is the unique primary key) ---
            if emp_id not in existing_emp_ids:
                db.add(models.Employee(emp_id=emp_id, name=name))
                existing_emp_ids.add(emp_id)
                new_employees += 1
            else:
                emp = db.get(models.Employee, emp_id)
                if emp and emp.name != name:
                    emp.name = name  # keep name in sync if it changed

            # --- Upsert Attendance (unique on emp_id + date) ---
            key = (emp_id, att_date)
            record_dict = {
                "emp_id": emp_id,
                "name": name,
                "date": str(att_date),
                "status": status,
                "check_in": check_in.strftime("%H:%M") if check_in else None,
                "check_out": check_out.strftime("%H:%M") if check_out else None,
            }
            if key in existing_att_keys:
                existing = (
                    db.query(models.Attendance)
                    .filter(models.Attendance.emp_id == emp_id, models.Attendance.date == att_date)
                    .first()
                )
                existing.status = status
                existing.check_in = check_in
                existing.check_out = check_out
                if comments is not None and comments.strip()!="":
                    existing.comments = comments  # only update if non-empty
                updated_attendance += 1
                if len(preview_updated) < 25:
                    preview_updated.append(record_dict)
            else:
                db.add(
                    models.Attendance(
                        emp_id=emp_id,
                        date=att_date,
                        status=status,
                        check_in=check_in,
                        check_out=check_out,
                        comments=comments,
                    )
                )
                existing_att_keys.add(key)
                inserted_attendance += 1
                if len(preview_inserted) < 25:
                    preview_inserted.append(record_dict)

        except Exception as exc:  # noqa: BLE001 - we want to capture and continue
            errors.append({"row": excel_row_no, "reason": f"Unexpected error: {exc}", "data": None})
            continue

    db.commit()

    import json

    log = models.UploadLog(
        filename=filename,
        total_rows=total_rows,
        new_employees=new_employees,
        inserted_attendance=inserted_attendance,
        updated_attendance=updated_attendance,
        error_rows=len(errors),
        errors_json=json.dumps(errors),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    log.preview_inserted = preview_inserted
    log.preview_updated = preview_updated
    log.errors_list = errors
    return log
