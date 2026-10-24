"""
Analytics endpoints (READ-ONLY - nothing here writes to the database).

  GET /api/analytics/filters           -> data for the filter dropdowns
  GET /api/analytics/attendance-graph  -> monthly / yearly attendance counts
  GET /api/analytics/daily-records     -> per-day check-in, check-out, hours worked
  GET /api/analytics/working-hours     -> daily / monthly / yearly hours summaries

All endpoints accept the same filters: emp_id, status (comma separated),
year / month, so the frontend can combine them freely.

Working-hours rule (nothing is invented):
  hours = check_out - check_in, ONLY when both exist and check_out > check_in.
  Otherwise the record is excluded from hour totals and flagged:
     no_timings | missing_check_in | missing_check_out | invalid_order
"""
import calendar
from collections import Counter, defaultdict
from datetime import date as date_cls, time as time_cls
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TIMING_NOTES = {
    "ok": None,
    "no_timings": "No check-in / check-out recorded",
    "missing_check_in": "Check-in missing",
    "missing_check_out": "Check-out missing",
    "invalid_order": "Check-out is not after check-in",
}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class GraphPoint(BaseModel):
    key: str
    label: str
    counts: Dict[str, int]
    total: int


class GraphResponse(BaseModel):
    view: str
    year: int
    month: Optional[int] = None
    emp_id: Optional[str] = None
    series: List[str]
    points: List[GraphPoint]
    totals: Dict[str, int]
    total_records: int


class DailyRecord(BaseModel):
    id: int
    emp_id: str
    name: str
    date: str
    status: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    worked_hours: Optional[float] = None      # decimal, e.g. 8.25
    worked_display: Optional[str] = None      # e.g. "8h 15m"
    timing_flag: str                          # ok | no_timings | ...
    timing_note: Optional[str] = None


class TimingSummary(BaseModel):
    valid_records: int
    excluded_records: int
    total_hours: Optional[float] = None
    avg_hours_per_day: Optional[float] = None
    excluded_breakdown: Dict[str, int] = {}


class RecordsResponse(BaseModel):
    total: int
    limit: int
    offset: int
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    summary: TimingSummary
    records: List[DailyRecord]


class HoursPoint(BaseModel):
    key: str
    label: str
    total_hours: Optional[float] = None       # None when no valid timings
    avg_hours_per_day: Optional[float] = None
    valid_records: int
    excluded_records: int
    employees_counted: int


class EmployeeHours(BaseModel):
    emp_id: str
    name: str
    total_hours: Optional[float] = None
    avg_hours_per_day: Optional[float] = None
    valid_days: int
    excluded_days: int


class HoursResponse(BaseModel):
    period: str
    year: Optional[int] = None
    month: Optional[int] = None
    emp_id: Optional[str] = None
    statuses: List[str]
    points: List[HoursPoint]
    totals: TimingSummary
    by_employee: List[EmployeeHours]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_seconds(t: time_cls) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second


def compute_hours(check_in: Optional[time_cls], check_out: Optional[time_cls]) -> Tuple[Optional[int], str]:
    """Return (worked_seconds or None, flag). Never guesses missing values."""
    if check_in is None and check_out is None:
        return None, "no_timings"
    if check_in is None:
        return None, "missing_check_in"
    if check_out is None:
        return None, "missing_check_out"
    diff = _to_seconds(check_out) - _to_seconds(check_in)
    if diff <= 0:
        return None, "invalid_order"
    return diff, "ok"


def _hours(seconds: Optional[int]) -> Optional[float]:
    return None if seconds is None else round(seconds / 3600, 2)


def _display(seconds: Optional[int]) -> Optional[str]:
    if seconds is None:
        return None
    h, m = divmod(int(round(seconds / 60)), 60)
    return f"{h}h {m:02d}m"


def _fmt_time(t: Optional[time_cls]) -> Optional[str]:
    return t.strftime("%H:%M") if t else None


def _parse_statuses(raw: Optional[str]) -> Optional[List[str]]:
    """'Present,WFH' -> ['Present','WFH']. Empty / 'All' -> None (no filter)."""
    if not raw:
        return None
    items = [s.strip() for s in raw.split(",") if s.strip()]
    if not items or any(s.lower() == "all" for s in items):
        return None
    allowed = {s.lower(): s for s in schemas.ALLOWED_STATUSES}
    resolved, bad = [], []
    for s in items:
        if s.lower() in allowed:
            resolved.append(allowed[s.lower()])
        else:
            bad.append(s)
    if bad:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status {bad}. Allowed: {', '.join(schemas.ALLOWED_STATUSES)}",
        )
    return resolved


def _resolve_employee(db: Session, emp_id: Optional[str]) -> Optional[str]:
    """None / '' / 'all' -> None (all employees). Unknown id -> 404."""
    if emp_id is None or not emp_id.strip() or emp_id.strip().lower() == "all":
        return None
    emp_id = emp_id.strip()
    if db.get(models.Employee, emp_id) is None:
        raise HTTPException(status_code=404, detail=f"Employee '{emp_id}' not found")
    return emp_id


def _apply_filters(q, start, end, emp_id, statuses):
    A = models.Attendance
    if start:
        q = q.filter(A.date >= start)
    if end:
        q = q.filter(A.date <= end)
    if emp_id:
        q = q.filter(A.emp_id == emp_id)
    if statuses:
        q = q.filter(A.status.in_(statuses))
    return q


def _month_range(year: int, month: int):
    return date_cls(year, month, 1), date_cls(year, month, calendar.monthrange(year, month)[1])


def _year_range(year: int):
    return date_cls(year, 1, 1), date_cls(year, 12, 31)


def _resolve_year_month(db: Session, year: Optional[int], month: Optional[int], need_month: bool):
    """Fill missing year/month with the latest data. (None, None) if DB is empty."""
    A = models.Attendance
    if year is None:
        latest = db.query(func.max(A.date)).scalar()
        if latest is None:
            return None, None
        year = latest.year
    if need_month and month is None:
        s, e = _year_range(year)
        last = db.query(func.max(A.date)).filter(A.date >= s, A.date <= e).scalar()
        month = last.month if last else 1
    return year, month


# ---------------------------------------------------------------------------
# 1) Filter options
# ---------------------------------------------------------------------------
@router.get("/filters")
def get_filters(db: Session = Depends(get_db)):
    A = models.Attendance
    rows = db.query(extract("year", A.date), extract("month", A.date)).distinct().all()
    months_by_year: Dict[str, List[int]] = defaultdict(list)
    for y, m in rows:
        months_by_year[str(int(y))].append(int(m))
    for y in months_by_year:
        months_by_year[y].sort()

    latest = db.query(func.max(A.date)).scalar()
    employees = db.query(models.Employee).order_by(models.Employee.name).all()
    return {
        "years": sorted(int(y) for y in months_by_year),
        "months_by_year": months_by_year,
        "latest_date": latest.isoformat() if latest else None,
        "statuses": list(schemas.ALLOWED_STATUSES),
        "employees": [{"emp_id": e.emp_id, "name": e.name} for e in employees],
    }


# ---------------------------------------------------------------------------
# 2) Attendance graph  (monthly = one bar per day, yearly = one bar per month)
# ---------------------------------------------------------------------------
@router.get("/attendance-graph", response_model=GraphResponse)
def attendance_graph(
    view: Literal["monthly", "yearly"] = "monthly",
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    emp_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="Comma separated, e.g. Present,WFH"),
    db: Session = Depends(get_db),
):
    statuses = _parse_statuses(status)
    series = statuses or list(schemas.ALLOWED_STATUSES)
    emp = _resolve_employee(db, emp_id)
    year, month = _resolve_year_month(db, year, month, need_month=(view == "monthly"))

    if year is None:  # empty database
        return GraphResponse(view=view, year=date_cls.today().year, series=series,
                             points=[], totals={s: 0 for s in series}, total_records=0)

    if view == "monthly":
        start, end = _month_range(year, month)
        skeleton = [(date_cls(year, month, d).isoformat(), str(d))
                    for d in range(1, end.day + 1)]
    else:
        start, end = _year_range(year)
        skeleton = [(f"{year}-{m:02d}", MONTH_LABELS[m - 1]) for m in range(1, 13)]
        month = None

    A = models.Attendance
    rows = _apply_filters(db.query(A.date, A.status), start, end, emp, statuses).all()

    counts = {key: {s: 0 for s in series} for key, _ in skeleton}
    for d, st in rows:
        key = d.isoformat() if view == "monthly" else f"{d.year}-{d.month:02d}"
        if key in counts and st in counts[key]:
            counts[key][st] += 1

    points = [GraphPoint(key=k, label=l, counts=counts[k], total=sum(counts[k].values()))
              for k, l in skeleton]
    totals = {s: sum(p.counts[s] for p in points) for s in series}
    return GraphResponse(view=view, year=year, month=month, emp_id=emp, series=series,
                         points=points, totals=totals, total_records=sum(totals.values()))


# ---------------------------------------------------------------------------
# 3) Daily records with check-in / check-out / hours worked
# ---------------------------------------------------------------------------
@router.get("/daily-records", response_model=RecordsResponse)
def daily_records(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    target_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD (single day)"),
    emp_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    statuses = _parse_statuses(status)
    emp = _resolve_employee(db, emp_id)

    if target_date:
        try:
            start = end = date_cls.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        if year is None:   # nothing given -> latest month with data
            year, month = _resolve_year_month(db, None, None, need_month=True)
        if year is None:   # empty database
            return RecordsResponse(total=0, limit=limit, offset=offset,
                                   summary=TimingSummary(valid_records=0, excluded_records=0),
                                   records=[])
        start, end = _month_range(year, month) if month else _year_range(year)

    A, E = models.Attendance, models.Employee
    q = db.query(A, E.name).join(E, E.emp_id == A.emp_id)
    rows = _apply_filters(q, start, end, emp, statuses).order_by(A.date.desc(), E.name.asc()).all()

    total_secs, valid, excluded = 0, 0, Counter()
    page: List[DailyRecord] = []
    for i, (rec, name) in enumerate(rows):
        secs, flag = compute_hours(rec.check_in, rec.check_out)
        if secs is None:
            excluded[flag] += 1
        else:
            valid += 1
            total_secs += secs
        if offset <= i < offset + limit:
            page.append(DailyRecord(
                id=rec.id, emp_id=rec.emp_id, name=name, date=rec.date.isoformat(),
                status=rec.status, check_in=_fmt_time(rec.check_in),
                check_out=_fmt_time(rec.check_out), worked_hours=_hours(secs),
                worked_display=_display(secs), timing_flag=flag,
                timing_note=TIMING_NOTES[flag],
            ))

    summary = TimingSummary(
        valid_records=valid,
        excluded_records=sum(excluded.values()),
        total_hours=_hours(total_secs) if valid else None,
        avg_hours_per_day=_hours(total_secs / valid) if valid else None,
        excluded_breakdown=dict(excluded),
    )
    return RecordsResponse(total=len(rows), limit=limit, offset=offset,
                           period_start=start.isoformat(), period_end=end.isoformat(),
                           summary=summary, records=page)


# ---------------------------------------------------------------------------
# 4) Working-hours analytics
#     period=daily   -> one point per day of the selected month
#     period=monthly -> one point per month of the selected year
#     period=yearly  -> one point per year found in the data
#   emp_id omitted / "all" -> whole team, plus by_employee breakdown
# ---------------------------------------------------------------------------
@router.get("/working-hours", response_model=HoursResponse)
def working_hours(
    period: Literal["daily", "monthly", "yearly"] = "daily",
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    emp_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    statuses = _parse_statuses(status)
    emp = _resolve_employee(db, emp_id)
    used_statuses = statuses or list(schemas.ALLOWED_STATUSES)

    start = end = None
    if period == "daily":
        year, month = _resolve_year_month(db, year, month, need_month=True)
        if year is None:
            year = month = None
        else:
            start, end = _month_range(year, month)
    elif period == "monthly":
        year, _ = _resolve_year_month(db, year, None, need_month=False)
        month = None
        if year is not None:
            start, end = _year_range(year)
    else:  # yearly
        year = month = None

    empty = HoursResponse(
        period=period, year=year, month=month, emp_id=emp, statuses=used_statuses,
        points=[], totals=TimingSummary(valid_records=0, excluded_records=0), by_employee=[],
    )
    if period != "yearly" and year is None:
        return empty

    A, E = models.Attendance, models.Employee
    q = db.query(A, E.name).join(E, E.emp_id == A.emp_id)
    rows = _apply_filters(q, start, end, emp, statuses).all()

    def bucket_key(d: date_cls) -> str:
        if period == "daily":
            return d.isoformat()
        if period == "monthly":
            return f"{d.year}-{d.month:02d}"
        return str(d.year)

    buckets = defaultdict(lambda: {"secs": 0, "valid": 0, "excluded": 0, "emps": set()})
    per_emp: Dict[str, dict] = {}
    excluded_breakdown = Counter()
    total_secs = valid_total = 0

    for rec, name in rows:
        secs, flag = compute_hours(rec.check_in, rec.check_out)
        b = buckets[bucket_key(rec.date)]
        e = per_emp.setdefault(rec.emp_id, {"name": name, "secs": 0, "valid": 0, "excluded": 0})
        if secs is None:
            b["excluded"] += 1
            e["excluded"] += 1
            excluded_breakdown[flag] += 1
        else:
            b["secs"] += secs
            b["valid"] += 1
            b["emps"].add(rec.emp_id)
            e["secs"] += secs
            e["valid"] += 1
            total_secs += secs
            valid_total += 1

    if period == "daily":
        skeleton = [(date_cls(year, month, d).isoformat(), str(d)) for d in range(1, end.day + 1)]
    elif period == "monthly":
        skeleton = [(f"{year}-{m:02d}", MONTH_LABELS[m - 1]) for m in range(1, 13)]
    else:
        skeleton = [(k, k) for k in sorted(buckets)]

    points = []
    for key, label in skeleton:
        b = buckets.get(key)
        if b and b["valid"]:
            points.append(HoursPoint(
                key=key, label=label, total_hours=_hours(b["secs"]),
                avg_hours_per_day=_hours(b["secs"] / b["valid"]),
                valid_records=b["valid"], excluded_records=b["excluded"],
                employees_counted=len(b["emps"])))
        else:
            points.append(HoursPoint(
                key=key, label=label, total_hours=None, avg_hours_per_day=None,
                valid_records=0, excluded_records=b["excluded"] if b else 0,
                employees_counted=0))

    by_employee = [
        EmployeeHours(
            emp_id=eid, name=v["name"],
            total_hours=_hours(v["secs"]) if v["valid"] else None,
            avg_hours_per_day=_hours(v["secs"] / v["valid"]) if v["valid"] else None,
            valid_days=v["valid"], excluded_days=v["excluded"])
        for eid, v in per_emp.items()
    ]
    by_employee.sort(key=lambda x: (-(x.total_hours or 0), x.name))

    totals = TimingSummary(
        valid_records=valid_total,
        excluded_records=sum(excluded_breakdown.values()),
        total_hours=_hours(total_secs) if valid_total else None,
        avg_hours_per_day=_hours(total_secs / valid_total) if valid_total else None,
        excluded_breakdown=dict(excluded_breakdown),
    )
    return HoursResponse(period=period, year=year, month=month, emp_id=emp,
                         statuses=used_statuses, points=points, totals=totals,
                         by_employee=by_employee)