
"""
Handles reading, validating and upserting attendance Excel files.

Features:
- Supports multiple Excel worksheets.
- Automatically detects the header row.
- Prevents duplicate employees.
- Prevents duplicate attendance for the same employee and date.
- Updates existing attendance records.
- Preserves attendance history.
- Supports sick leave, weekly holiday, public holiday and other leave types.
- Collects invalid rows without stopping the entire upload.
"""

import io
import json
import re

from datetime import date as date_cls
from datetime import datetime, time as time_cls

import pandas as pd
from sqlalchemy.orm import Session

from . import models


# =========================================================
# ATTENDANCE STATUSES
# =========================================================

VALID_STATUSES = {
    "present": "Present",
    "p": "Present",

    "absent": "Absent",
    "a": "Absent",

    "wfh": "WFH",
    "workfromhome": "WFH",
    "workingfromhome": "WFH",

    "leave": "Leave",
    "l": "Leave",
    "onleave": "Leave",

    "halfday": "Half Day",
    "hd": "Half Day",

 
   
    
    "casualsickleave": "Casual/Sick Leave",
    "casualleave": "Casual/Sick Leave",
    "casualsick": "Casual/Sick Leave",

    "publicholiday": "Public Holiday",
    "public": "Public Holiday",

    "weeklyholiday": "Weekly Holiday",
    "weeklyoff": "Weekly Holiday",
    "weekoff": "Weekly Holiday",

    "earnedleave": "Earned Leave",
    "el": "Earned Leave",

    "compensatoryoff": "Compensatory Leave",
    "compoff": "Compensatory Leave",
    "compensatoryleave": "Compensatory Leave",

    "optionalholiday": "Optional Holiday",
}


# =========================================================
# EXCEL COLUMN ALIASES
# =========================================================

COLUMN_ALIASES = {
    "emp_id": [
        "empno",
        "empid",
        "employeeid",
        "employeeno",
        "employeeidno",
        "employee number",
    ],

    "name": [
        "employeename",
        "name",
        "empname",
    ],

    "date": [
        "date",
        "attendancedate",
        "attdate",
    ],

    "status": [
        "attendancestatus",
        "status",
        "attendance",
    ],

    "check_in": [
        "checkin",
        "intime",
        "in time",
    ],

    "check_out": [
        "checkout",
        "outtime",
        "out time",
    ],

    "comments": [
        "comments",
        "comment",
        "remarks",
        "notes",
    ],
}


# =========================================================
# COMMON HELPERS
# =========================================================

def _is_missing(value):

    if value is None:
        return True

    try:
        result = pd.isna(value)

        if isinstance(result, bool):
            return result

        return False

    except (TypeError, ValueError):
        return False


def _normalize_text(value):

    if _is_missing(value):
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def _normalize_header(value):

    if _is_missing(value):
        return ""

    value = str(value).replace("\ufeff", "").strip()

    return _normalize_text(value)


def _has_time_value(value):

    if _is_missing(value):
        return False

    return str(value).strip().lower() not in {
        "",
        "nan",
        "nat",
        "none",
        "-",
        "null",
    }


# =========================================================
# MAP EXCEL COLUMNS
# =========================================================

def _map_columns(df):

    normalized = {}

    for column in df.columns:

        key = _normalize_header(column)

        if key and key not in normalized:
            normalized[key] = column

    mapping = {}

    for canonical, aliases in COLUMN_ALIASES.items():

        found = None

        for alias in aliases:

            alias_key = _normalize_header(alias)

            if alias_key in normalized:

                found = normalized[alias_key]
                break

        mapping[canonical] = found

    required = (
        "emp_id",
        "name",
        "date",
        "status",
    )

    missing = [
        column
        for column in required
        if mapping[column] is None
    ]

    if missing:

        raise ValueError(
            "Missing required Excel columns: "
            + ", ".join(missing)
            + ". Expected: Emp No, Employee Name, "
              "Date and Attendance Status."
        )

    return mapping


# =========================================================
# LOAD EXCEL AND DETECT HEADER ROW
# =========================================================

def _load_attendance_excel(file_bytes):

    """
    Detect the worksheet and header row.
    Supports blank rows and multiple worksheets.

    Returns:
        dataframe, column mapping, header row index
    """

    try:

        workbook = pd.ExcelFile(
            io.BytesIO(file_bytes),
            engine="openpyxl"
        )

        for sheet_name in workbook.sheet_names:

            raw = pd.read_excel(
                workbook,
                sheet_name=sheet_name,
                header=None
            )

            for row_index in range(min(30, len(raw))):

                headers = raw.iloc[row_index].tolist()

                if all(
                    _is_missing(value)
                    for value in headers
                ):
                    continue

                # Make duplicate/blank headings unique.
                safe_headers = []
                used = set()

                for index, header in enumerate(headers):

                    label = (
                        str(header).strip()
                        if not _is_missing(header)
                        else f"__empty_{index}"
                    )

                    if label in used:
                        label = f"{label}_{index}"

                    used.add(label)
                    safe_headers.append(label)

                header_df = pd.DataFrame(
                    columns=safe_headers
                )

                try:

                    col_map = _map_columns(header_df)

                except ValueError:
                    continue

                df = raw.iloc[row_index + 1:].copy()

                df.columns = safe_headers

                df = (
                    df.dropna(how="all")
                    .reset_index(drop=True)
                )

                if not df.empty:

                    return df, col_map, row_index

        raise ValueError(
            "Could not find attendance header row. "
            "Required columns: Emp No, Employee Name, "
            "Date and Attendance Status."
        )

    except Exception as exc:

        raise ValueError(
            f"Could not read Excel file: {exc}"
        ) from exc


# =========================================================
# DATE PARSER
# =========================================================

def _parse_date(value):

    if _is_missing(value):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date_cls):
        return value

    try:

        parsed = pd.to_datetime(
            str(value).strip(),
            dayfirst=True,
            errors="coerce"
        )

        if pd.isna(parsed):
            return None

        return parsed.date()

    except (TypeError, ValueError, OverflowError):
        return None


# =========================================================
# TIME PARSER
# =========================================================

def _parse_time(value):

    """
    Supports:
    - Excel time values
    - Python datetime.time
    - Python datetime
    - 13:42
    - 13:42:00
    - 1:42 PM
    - 1:42:00 PM
    - Date-time strings
    - Excel numeric time fractions
    """

    if _is_missing(value):
        return None

    if isinstance(value, time_cls):

        return value.replace(microsecond=0)

    if isinstance(value, (datetime, pd.Timestamp)):

        return value.time().replace(microsecond=0)

    if isinstance(value, (int, float)):

        numeric_value = float(value)

        if 0 <= numeric_value < 1:

            total_seconds = round(
                numeric_value * 24 * 60 * 60
            )

            total_seconds %= 24 * 60 * 60

            hours, remainder = divmod(
                total_seconds,
                3600
            )

            minutes, seconds = divmod(
                remainder,
                60
            )

            return time_cls(
                int(hours),
                int(minutes),
                int(seconds)
            )

        return None

    text = str(value).strip()

    if text.lower() in {
        "",
        "nan",
        "nat",
        "none",
        "-",
        "null",
    }:
        return None

    text = re.sub(
        r"(?i)(\d)(am|pm)$",
        r"\1 \2",
        text
    )

    text = re.sub(r"\s+", " ", text).strip()

    formats = (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M %p",
        "%I:%M:%S %p",
        "%d %b %Y %I:%M %p",
        "%b %d %Y %I:%M %p",
        "%d %B %Y %I:%M %p",
        "%B %d %Y %I:%M %p",
    )

    for fmt in formats:

        try:

            return datetime.strptime(
                text,
                fmt
            ).time()

        except ValueError:
            continue

    try:

        parsed = pd.to_datetime(
            text,
            errors="coerce"
        )

        if not pd.isna(parsed):

            return parsed.time().replace(
                microsecond=0
            )

    except (TypeError, ValueError, OverflowError):
        pass

    return None


# =========================================================
# STATUS PARSER
# =========================================================

def _parse_status(value):

    if _is_missing(value):
        return None

    key = _normalize_text(value)

    return VALID_STATUSES.get(key)


# =========================================================
# MAIN EXCEL PROCESSOR
# =========================================================

def process_excel_file(
    db: Session,
    filename: str,
    file_bytes: bytes
) -> models.UploadLog:

    """
    Read Excel, validate rows and insert/update
    employees and attendance records.
    """

    # -----------------------------------------------------
    # LOAD EXCEL
    # -----------------------------------------------------

    df, col_map, header_row_index = (
        _load_attendance_excel(file_bytes)
    )

    if df.empty:

        raise ValueError(
            "The uploaded Excel file contains no data rows."
        )

    total_rows = len(df)

    new_employees = 0
    inserted_attendance = 0
    updated_attendance = 0

    errors = []

    preview_inserted = []
    preview_updated = []

    # -----------------------------------------------------
    # LOAD EXISTING EMPLOYEES
    # -----------------------------------------------------

    employee_objects = {

        employee.emp_id: employee

        for employee in db.query(
            models.Employee
        ).all()

    }

    # -----------------------------------------------------
    # LOAD EXISTING ATTENDANCE
    # -----------------------------------------------------

    attendance_objects = {

        (record.emp_id, record.date): record

        for record in db.query(
            models.Attendance
        ).all()

    }

    # -----------------------------------------------------
    # PROCESS EACH EXCEL ROW
    # -----------------------------------------------------

    for index, row in df.iterrows():

        excel_row_no = index + header_row_index + 2

        try:

            raw_emp_id = row.get(
                col_map["emp_id"]
            )

            raw_name = row.get(
                col_map["name"]
            )

            raw_date = row.get(
                col_map["date"]
            )

            raw_status = row.get(
                col_map["status"]
            )

            raw_checkin = (
                row.get(col_map["check_in"])
                if col_map["check_in"] is not None
                else None
            )

            raw_checkout = (
                row.get(col_map["check_out"])
                if col_map["check_out"] is not None
                else None
            )

            raw_comments = (
                row.get(col_map["comments"])
                if col_map["comments"] is not None
                else None
            )

            # ---------------------------------------------
            # VALIDATE EMPLOYEE ID
            # ---------------------------------------------

            if (
                _is_missing(raw_emp_id)
                or not str(raw_emp_id).strip()
            ):

                errors.append({
                    "row": excel_row_no,
                    "reason": "Missing Employee ID",
                    "data": None,
                })

                continue

            emp_id = str(raw_emp_id).strip()

            if re.fullmatch(r"\d+\.0", emp_id):
                emp_id = emp_id[:-2]

            # ---------------------------------------------
            # VALIDATE EMPLOYEE NAME
            # ---------------------------------------------

            if (
                _is_missing(raw_name)
                or not str(raw_name).strip()
            ):

                errors.append({
                    "row": excel_row_no,
                    "reason": (
                        f"Missing Employee Name for {emp_id}"
                    ),
                    "data": None,
                })

                continue

            name = str(raw_name).strip()

            # ---------------------------------------------
            # VALIDATE DATE
            # ---------------------------------------------

            att_date = _parse_date(raw_date)

            if att_date is None:

                errors.append({
                    "row": excel_row_no,
                    "reason": (
                        f"Invalid or missing Date for {emp_id}"
                    ),
                    "data": None,
                })

                continue

            # ---------------------------------------------
            # VALIDATE STATUS
            # ---------------------------------------------

            status = _parse_status(raw_status)

            if status is None:

                errors.append({
                    "row": excel_row_no,
                    "reason": (
                        f"Invalid attendance status "
                        f"'{raw_status}' for {emp_id}"
                    ),
                    "data": None,
                })

                continue

            # ---------------------------------------------
            # VALIDATE CHECK-IN
            # ---------------------------------------------

            check_in = _parse_time(raw_checkin)

            if (
                _has_time_value(raw_checkin)
                and check_in is None
            ):

                errors.append({
                    "row": excel_row_no,
                    "reason": (
                        f"Invalid CheckIn time "
                        f"'{raw_checkin}' for {emp_id}"
                    ),
                    "data": None,
                })

                continue

            # ---------------------------------------------
            # VALIDATE CHECK-OUT
            # ---------------------------------------------

            check_out = _parse_time(raw_checkout)

            if (
                _has_time_value(raw_checkout)
                and check_out is None
            ):

                errors.append({
                    "row": excel_row_no,
                    "reason": (
                        f"Invalid CheckOut time "
                        f"'{raw_checkout}' for {emp_id}"
                    ),
                    "data": None,
                })

                continue

            # ---------------------------------------------
            # COMMENTS
            # ---------------------------------------------

            comments = (
                None
                if _is_missing(raw_comments)
                else str(raw_comments).strip()
            )

            if comments == "":
                comments = None

            # ---------------------------------------------
            # INSERT OR UPDATE EMPLOYEE
            # ---------------------------------------------

            employee = employee_objects.get(emp_id)

            if employee is None:

                employee = models.Employee(
                    emp_id=emp_id,
                    name=name
                )

                db.add(employee)

                employee_objects[emp_id] = employee

                new_employees += 1

            else:

                if employee.name != name:
                    employee.name = name

            # ---------------------------------------------
            # INSERT OR UPDATE ATTENDANCE
            # ---------------------------------------------

            key = (emp_id, att_date)

            existing = attendance_objects.get(key)

            record_dict = {
                "emp_id": emp_id,
                "name": name,
                "date": str(att_date),
                "status": status,
                "check_in": (
                    check_in.strftime("%H:%M")
                    if check_in else None
                ),
                "check_out": (
                    check_out.strftime("%H:%M")
                    if check_out else None
                ),
                "comments": comments,
            }

            if existing is not None:

                # Update existing record.

                existing.status = status
                existing.check_in = check_in
                existing.check_out = check_out

                # Preserve old comments if Excel is blank.

                if comments is not None:
                    existing.comments = comments

                updated_attendance += 1

                if len(preview_updated) < 25:
                    preview_updated.append(record_dict)

            else:

                # Insert new attendance record.

                attendance = models.Attendance(
                    emp_id=emp_id,
                    date=att_date,
                    status=status,
                    check_in=check_in,
                    check_out=check_out,
                    comments=comments,
                )

                db.add(attendance)

                # Prevent duplicate rows within the same upload.

                attendance_objects[key] = attendance

                inserted_attendance += 1

                if len(preview_inserted) < 25:
                    preview_inserted.append(record_dict)

        except Exception as exc:

            errors.append({
                "row": excel_row_no,
                "reason": f"Unexpected error: {exc}",
                "data": None,
            })

            continue

    # -----------------------------------------------------
    # SAVE DATABASE CHANGES
    # -----------------------------------------------------

    try:

        db.commit()

    except Exception as exc:

        db.rollback()

        raise ValueError(
            f"Database error while saving Excel records: {exc}"
        ) from exc

    # -----------------------------------------------------
    # CREATE UPLOAD LOG
    # -----------------------------------------------------

    try:

        log = models.UploadLog(
            filename=filename,
            total_rows=total_rows,
            new_employees=new_employees,
            inserted_attendance=inserted_attendance,
            updated_attendance=updated_attendance,
            error_rows=len(errors),
            errors_json=json.dumps(
                errors,
                default=str
            ),
        )

        db.add(log)

        db.commit()

        db.refresh(log)

    except Exception as exc:

        db.rollback()

        raise ValueError(
            f"Could not save upload log: {exc}"
        ) from exc

    # -----------------------------------------------------
    # RETURN PREVIEW INFORMATION
    # -----------------------------------------------------

    log.preview_inserted = preview_inserted

    log.preview_updated = preview_updated

    log.errors_list = errors

    return log
