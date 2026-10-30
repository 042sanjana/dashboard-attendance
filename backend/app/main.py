"""
Employee Attendance Dashboard - FastAPI backend entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import os
from datetime import date as date_cls, timedelta
from typing import Optional, List

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from .excel_processor import process_excel_file
from .analytics import router as analytics_router      # <-- add this line

from . import models, schemas
from .database import engine, get_db
from .excel_processor import process_excel_file


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Employee Attendance Dashboard API",
    description="API for uploading and managing employee attendance data.",
    version="1.0.0",
)
app.include_router(analytics_router) # <-- add this line


# ============================================================
# DATABASE STARTUP
# ============================================================

# IMPORTANT:
# Do NOT delete the database whenever FastAPI restarts.
#
# If you really want to recreate the database manually, set:
#
# RESET_ON_STARTUP=true
#
# Otherwise the default is false.
RESET_ON_STARTUP = (
    os.environ.get("RESET_ON_STARTUP", "false")
    .strip()
    .lower()
    in ("1", "true", "yes")
)


@app.on_event("startup")
def on_startup():
    if RESET_ON_STARTUP:
        models.Base.metadata.drop_all(bind=engine)

    models.Base.metadata.create_all(bind=engine)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ALLOWED_EXTENSIONS = (".xlsx", ".xls")
MAX_FILE_SIZE_MB = 15


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload", response_model=schemas.UploadResult)
async def upload_attendance_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    filename = file.filename or ""

    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type '{filename}'. "
                "Only .xlsx or .xls files are accepted."
            ),
        )

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit.",
        )

    try:
        log = process_excel_file(
            db,
            filename,
            file_bytes,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {exc}",
        )

    return schemas.UploadResult(
        filename=log.filename,
        total_rows=log.total_rows,
        new_employees=log.new_employees,
        inserted_attendance=log.inserted_attendance,
        updated_attendance=log.updated_attendance,
        error_rows=log.error_rows,
        errors=[
            schemas.UploadRowError(**e)
            for e in log.errors_list
        ],
        preview_inserted=log.preview_inserted,
        preview_updated=log.preview_updated,
    )


# ============================================================
# RESET ALL DATA
# ============================================================

def _perform_reset(db: Session):
    """
    Delete all attendance, employees and upload history.
    """

    deleted_attendance = (
        db.query(models.Attendance).delete(
            synchronize_session=False
        )
    )

    deleted_employees = (
        db.query(models.Employee).delete(
            synchronize_session=False
        )
    )

    deleted_logs = (
        db.query(models.UploadLog).delete(
            synchronize_session=False
        )
    )

    db.commit()

    return {
        "message": "All data has been reset. The dashboard is now empty.",
        "deleted_attendance": deleted_attendance,
        "deleted_employees": deleted_employees,
        "deleted_upload_logs": deleted_logs,
    }


# POST is used by the current React ResetDataButton.
@app.post("/api/reset")
def reset_all_data_post(
    db: Session = Depends(get_db),
):
    try:
        return _perform_reset(db)
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset data: {exc}",
        )


# DELETE is also supported so both methods work.
@app.delete("/api/reset")
def reset_all_data_delete(
    db: Session = Depends(get_db),
):
    try:
        return _perform_reset(db)
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset data: {exc}",
        )


# ============================================================
# UPLOAD HISTORY
# ============================================================

@app.get("/api/uploads/history")
def upload_history(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    logs = (
        db.query(models.UploadLog)
        .order_by(models.UploadLog.uploaded_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "filename": log.filename,
            "uploaded_at": log.uploaded_at,
            "total_rows": log.total_rows,
            "new_employees": log.new_employees,
            "inserted_attendance": log.inserted_attendance,
            "updated_attendance": log.updated_attendance,
            "error_rows": log.error_rows,
        }
        for log in logs
    ]


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def _status_counts(
    db: Session,
    target_date: Optional[date_cls],
):
    query = db.query(
        models.Attendance.status,
        func.count(models.Attendance.id),
    )

    if target_date:
        query = query.filter(
            models.Attendance.date == target_date
        )

    query = query.group_by(models.Attendance.status)

    counts = {
        status:0
        for status in schemas.ALLOWED_STATUSES
    }

    for status, count in query.all():
        if status in counts:
            counts[status] = count

    return counts


@app.get(
    "/api/summary",
    response_model=schemas.SummaryOut,
)
def get_summary(
    target_date: Optional[str] = Query(
        None,
        alias="date",
    ),
    db: Session = Depends(get_db),
):
    parsed_date = None

    if target_date:
        try:
            parsed_date = date_cls.fromisoformat(
                target_date
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="date must be in YYYY-MM-DD format",
            )
    else:
        parsed_date = (
            db.query(
                func.max(models.Attendance.date)
            ).scalar()
        )

    total_employees = (
        db.query(
            func.count(models.Employee.emp_id)
        ).scalar()
        or 0
    )

    counts = _status_counts(
        db,
        parsed_date,
    )

    return schemas.SummaryOut(
        total_employees=total_employees,
        present=counts["Present"],
        absent=counts["Absent"],
        wfh=counts["WFH"],
        leave=counts["Leave"],
        half_day=counts["Half Day"],
        date=(
            parsed_date.isoformat()
            if parsed_date
            else None
        ),
    )


# ============================================================
# CHART DATA
# ============================================================

@app.get(
    "/api/chart-data",
    response_model=List[schemas.ChartPoint],
)
def get_chart_data(
    days: int = Query(14, ge=1, le=365),
    db: Session = Depends(get_db),
):
    latest = (
        db.query(
            func.max(models.Attendance.date)
        ).scalar()
    )

    if not latest:
        return []

    start = latest - timedelta(days=days - 1)

    rows = (
        db.query(
            models.Attendance.date,
            models.Attendance.status,
            func.count(models.Attendance.id),
        )
        .filter(
            models.Attendance.date >= start,
            models.Attendance.date <= latest,
        )
        .group_by(
            models.Attendance.date,
            models.Attendance.status,
        )
        .all()
    )

    by_date = {}

    current = start

    while current <= latest:
        by_date[current.isoformat()] = {
            "present": 0,
            "absent": 0,
            "wfh": 0,
            "leave": 0,
            "half_day": 0,
            "sick_leave": 0,
            "public_holiday": 0,
            "weekly_holiday": 0,
            "earned_leave": 0,
            "compensatory_leave": 0,
            "optional_holiday": 0,
        }

        current += timedelta(days=1)

    key_map = {
        "Present": "present",
        "Absent": "absent",
        "WFH": "wfh",
        "Leave": "leave",
        "Half Day": "half_day",
        "Sick leave": "sick_leave",
        "Public Holiday": "public_holiday",
        "Weekly Holiday": "weekly_holiday",
        "Earned Leave": "earned_leave",
        "Compensatory Leave": "compensatory_leave",
        "Optional Holiday": "optional_holiday",
    }

    for record_date, status, count in rows:
        iso = record_date.isoformat()

        if (
            iso in by_date
            and status in key_map
        ):
            by_date[iso][key_map[status]] = count

    return [
        schemas.ChartPoint(
            date=key,
            **values,
        )
        for key, values
        in sorted(by_date.items())
    ]


# ============================================================
# STATUS DISTRIBUTION
# ============================================================

@app.get("/api/status-distribution")
def get_status_distribution(
    target_date: Optional[str] = Query(
        None,
        alias="date",
    ),
    db: Session = Depends(get_db),
):
    parsed_date = None

    if target_date:
        try:
            parsed_date = date_cls.fromisoformat(
                target_date
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="date must be in YYYY-MM-DD format",
            )
    else:
        parsed_date = (
            db.query(
                func.max(models.Attendance.date)
            ).scalar()
        )

    counts = _status_counts(
        db,
        parsed_date,
    )

    return [
        {
            "name": key,
            "value": value,
        }
        for key, value in counts.items()
    ]


# ============================================================
# EMPLOYEES - READ
# ============================================================

@app.get(
    "/api/employees",
    response_model=List[schemas.EmployeeWithStats],
)
def list_employees(
    search: Optional[str] = None,
    status: Optional[str] = None,
    target_date: Optional[str] = Query(
        None,
        alias="date",
    ),
    db: Session = Depends(get_db),
):
    query = db.query(models.Employee)

    if search:
        search_value = search.strip()

        if search_value:
            like = f"%{search_value}%"

            query = query.filter(
                (
                    models.Employee.name.ilike(like)
                )
                |
                (
                    models.Employee.emp_id.ilike(like)
                )
            )

    employees = (
        query
        .order_by(models.Employee.emp_id)
        .all()
    )

    parsed_date = None

    if target_date:
        try:
            parsed_date = date_cls.fromisoformat(
                target_date
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="date must be in YYYY-MM-DD format",
            )

    result = []

    for emp in employees:
        records = emp.attendance_records

        latest = records[0] if records else None

        if status:
            if parsed_date:
                matches = any(
                    record.date == parsed_date
                    and record.status == status
                    for record in records
                )

                if not matches:
                    continue

            elif (
                not latest
                or latest.status != status
            ):
                continue

        if parsed_date:
            day_record = next(
                (
                    record
                    for record in records
                    if record.date == parsed_date
                ),
                None,
            )

            latest_status = (
                day_record.status
                if day_record
                else None
            )

            latest_date = (
                parsed_date
                if day_record
                else None
            )

        else:
            latest_status = (
                latest.status
                if latest
                else None
            )

            latest_date = (
                latest.date
                if latest
                else None
            )

        result.append(
            schemas.EmployeeWithStats(
                emp_id=emp.emp_id,
                name=emp.name,
                latest_status=latest_status,
                latest_date=latest_date,
                present_count=sum(
                    1
                    for record in records
                    if record.status == "Present"
                ),
                absent_count=sum(
                    1
                    for record in records
                    if record.status == "Absent"
                ),
                wfh_count=sum(
                    1
                    for record in records
                    if record.status == "WFH"
                ),
                leave_count=sum(
                    1
                    for record in records
                    if record.status == "Leave"
                ),
                total_records=len(records),
            )
        )

    return result


# ============================================================
# EMPLOYEE - READ DETAIL
# ============================================================

@app.get(
    "/api/employees/{emp_id}",
    response_model=schemas.EmployeeDetail,
)
def get_employee_detail(
    emp_id: str,
    db: Session = Depends(get_db),
):
    emp = db.get(
        models.Employee,
        emp_id,
    )

    if not emp:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return schemas.EmployeeDetail(
        emp_id=emp.emp_id,
        name=emp.name,
        attendance=[
            schemas.AttendanceOut.model_validate(record)
            for record in emp.attendance_records
        ],
    )


# ============================================================
# EMPLOYEE - CREATE
# ============================================================

@app.post(
    "/api/employees",
    response_model=schemas.EmployeeOut,
    status_code=201,
)
def create_employee(
    payload: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
):
    emp_id = payload.emp_id.strip()
    name = payload.name.strip()

    if not emp_id or not name:
        raise HTTPException(
            status_code=422,
            detail="emp_id and name are required.",
        )

    existing = db.get(
        models.Employee,
        emp_id,
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Employee '{emp_id}' already exists.",
        )

    employee = models.Employee(
        emp_id=emp_id,
        name=name,
    )

    db.add(employee)

    try:
        db.commit()
        db.refresh(employee)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create employee.",
        )

    return employee


# ============================================================
# EMPLOYEE - UPDATE
# ============================================================

@app.put(
    "/api/employees/{emp_id}",
    response_model=schemas.EmployeeOut,
)
def update_employee(
    emp_id: str,
    payload: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
):
    employee = db.get(
        models.Employee,
        emp_id,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="name cannot be empty.",
        )

    employee.name = name

    try:
        db.commit()
        db.refresh(employee)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update employee.",
        )

    return employee


# ============================================================
# EMPLOYEE - DELETE
# ============================================================

@app.delete(
    "/api/employees/{emp_id}",
    status_code=204,
)
def delete_employee(
    emp_id: str,
    db: Session = Depends(get_db),
):
    employee = db.get(
        models.Employee,
        emp_id,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    db.delete(employee)

    try:
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to delete employee.",
        )

    return None


# ============================================================
# ATTENDANCE - READ
# ============================================================

@app.get(
    "/api/attendance",
    response_model=List[schemas.AttendanceOut],
)
def list_attendance(
    target_date: Optional[str] = Query(
        None,
        alias="date",
    ),
    emp_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Attendance)

    if target_date:
        try:
            parsed_date = date_cls.fromisoformat(
                target_date
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="date must be in YYYY-MM-DD format",
            )

        query = query.filter(
            models.Attendance.date == parsed_date
        )

    if emp_id:
        query = query.filter(
            models.Attendance.emp_id == emp_id
        )

    if status:
        _validate_status(status)

        query = query.filter(
            models.Attendance.status == status
        )

    return (
        query
        .order_by(
            models.Attendance.date.desc()
        )
        .limit(500)
        .all()
    )


# ============================================================
# ATTENDANCE STATUS VALIDATION
# ============================================================

def _validate_status(status: str):
    if status not in schemas.ALLOWED_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid status '{status}'. "
                "Must be one of: "
                + ", ".join(
                    schemas.ALLOWED_STATUSES
                )
            ),
        )


# ============================================================
# ATTENDANCE - CREATE
# ============================================================

@app.post(
    "/api/attendance",
    response_model=schemas.AttendanceOut,
    status_code=201,
)
def create_attendance(
    payload: schemas.AttendanceCreate,
    db: Session = Depends(get_db),
):
    employee = db.get(
        models.Employee,
        payload.emp_id,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Employee '{payload.emp_id}' "
                "does not exist."
            ),
        )

    _validate_status(payload.status)

    existing = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.emp_id
            == payload.emp_id,
            models.Attendance.date
            == payload.date,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"An attendance record already exists "
                f"for {payload.emp_id} on {payload.date}. "
                "Use update instead."
            ),
        )

    record = models.Attendance(
        emp_id=payload.emp_id,
        date=payload.date,
        status=payload.status,
        check_in=payload.check_in,
        check_out=payload.check_out,
        comments=payload.comments,
    )

    db.add(record)

    try:
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to create attendance record.",
        )

    return record


# ============================================================
# ATTENDANCE - UPDATE
# ============================================================

@app.put(
    "/api/attendance/{record_id}",
    response_model=schemas.AttendanceOut,
)
def update_attendance(
    record_id: int,
    payload: schemas.AttendanceUpdate,
    db: Session = Depends(get_db),
):
    record = db.get(
        models.Attendance,
        record_id,
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    if (
        "status" in updates
        and updates["status"] is not None
    ):
        _validate_status(
            updates["status"]
        )

    new_date = updates.get(
        "date",
        record.date,
    )

    if new_date != record.date:
        clash = (
            db.query(models.Attendance)
            .filter(
                models.Attendance.emp_id
                == record.emp_id,
                models.Attendance.date
                == new_date,
                models.Attendance.id
                != record.id,
            )
            .first()
        )

        if clash:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{record.emp_id} already has "
                    f"an attendance record on {new_date}."
                ),
            )

    for field, value in updates.items():
        setattr(
            record,
            field,
            value,
        )
    if "comments" in updates:
        record.comments = updates["comments"]  # Allow clearing comments
    try:
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to update attendance record.",
        )

    return record


# ============================================================
# ATTENDANCE - DELETE
# ============================================================

@app.delete(
    "/api/attendance/{record_id}",
    status_code=204,
)
def delete_attendance(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = db.get(
        models.Attendance,
        record_id,
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found",
        )

    db.delete(record)

    try:
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to delete attendance record.",
        )

    return None
# ODC Tracker is a separate module with isolated tables and API routes.
from .odc_tracker import router as odc_router
app.include_router(odc_router)
