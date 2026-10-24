# Employee Attendance Dashboard

A full-stack HR attendance system: **React.js** (frontend) + **FastAPI** (backend) + **SQLite** (database).

Admins upload an Excel file of daily attendance; the system automatically creates new
employees, inserts/updates attendance records without duplicates, and the dashboard
(summary cards, charts, searchable table, employee history) refreshes instantly.

---

## 1. Project Structure

```
attendance-dashboard/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app + all API routes
│   │   ├── models.py            # SQLAlchemy models (Employee, Attendance, UploadLog)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── database.py          # SQLite engine/session setup
│   │   └── excel_processor.py   # Excel validation + upsert logic
│   ├── requirements.txt
│   ├── generate_sample_data.py  # creates sample_attendance.xlsx for testing
│   └── sample_attendance.xlsx
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Topbar.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── SummaryCards.jsx
│   │   │   ├── AttendanceTrendChart.jsx
│   │   │   ├── StatusPieChart.jsx
│   │   │   ├── EmployeeTable.jsx
│   │   │   ├── EmployeeDetail.jsx
│   │   │   ├── UploadModal.jsx
│   │   │   └── StatusBadge.jsx
│   │   ├── api.js               # axios API client
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css            # full dashboard styling
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md   (this file)
```

---

## 2. Database Design

**Employees**
| Column | Type | Notes |
|---|---|---|
| emp_id | String | **Primary key** — the unique identifier from "Emp No" |
| name | String | Employee name (kept in sync if it changes on re-upload) |
| created_at / updated_at | DateTime | audit timestamps |

**Attendance**
| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key (autoincrement) |
| emp_id | String | Foreign key → employees.emp_id |
| date | Date | Attendance date |
| status | String | Present / Absent / WFH / Leave / Half Day |
| check_in / check_out | Time | Nullable |
| comments | Text | Nullable |
| **UNIQUE(emp_id, date)** | | Guarantees one record per employee per day |

**UploadLog** — records every upload's filename, row counts, and errors (for audit/history).

### Duplicate-safe upload logic
On every Excel upload the backend:
1. Validates required columns and each row (date, status, emp id).
2. For each valid row: inserts the employee **only if `emp_id` doesn't already exist**;
   otherwise it is left untouched (name refreshed if it changed).
3. For attendance: if `(emp_id, date)` already exists, the existing row is **updated**
   (status/check-in/check-out/comments); if not, a **new row is inserted**. Nothing is
   ever duplicated, and history for other dates is never touched — so uploading the same
   file (or overlapping date ranges) repeatedly is always safe.
4. Bad rows are collected as errors and skipped without failing the rest of the upload.

---

## 3. Prerequisites

- Python 3.10+
- Node.js 18+ and npm

---

## 4. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

# (optional) generate a sample Excel file to test with
python generate_sample_data.py

# run the API server
uvicorn app.main:app --reload --port 8000
```

The API will be live at **http://localhost:8000** (interactive docs at
`http://localhost:8000/docs`). A SQLite file `attendance.db` is created automatically
on first run — no manual migration step needed.

### Excel format expected

| Emp No | Employee Name | Date | Attendance Status | CheckIn | CheckOut | Comments |
|---|---|---|---|---|---|---|
| EMP001 | Aarav Sharma | 2026-09-23 | Present | 09:15 | 18:10 | |
| EMP002 | Priya Nair | 2026-09-23 | WFH | 09:30 | 18:00 | |

- Column headers are matched case-insensitively and tolerate common variants
  (e.g. "Emp No" / "EmpNo" / "Employee ID").
- `Attendance Status` accepts: `Present`, `Absent`, `WFH`, `Leave`, `Half Day`
  (and common abbreviations like `P`, `A`, `HD`).
- `Date` accepts most common formats (`YYYY-MM-DD`, `DD/MM/YYYY`, etc).

---

## 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api/*` requests to the
backend at `http://localhost:8000` (see `vite.config.js`), so both servers must be
running at the same time during development.

### Production build

```bash
npm run build
```

This outputs static files to `frontend/dist/` which you can serve with any static
file host (nginx, `serve`, etc.) — just point it at your deployed FastAPI backend
URL by adjusting the proxy / API base URL in `src/api.js`.

---

## 6. Running Both Together (quick start)

```bash
# terminal 1
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend && npm run dev
```

Then visit **http://localhost:5173**, click **Upload Excel**, and select
`backend/sample_attendance.xlsx` (or your own file) to see the dashboard populate.

---

## 7. Key Features

- **Sidebar navigation** + sticky topbar with live date and quick upload access.
- **Summary cards**: Total Employees, Present, WFH, Absent, On Leave — for the
  selected date.
- **Charts** (Recharts): 14-day attendance trend line chart + status breakdown pie chart.
- **Searchable, filterable employee table** with color-coded status badges, per-employee
  present/absent/WFH counts, and a date picker.
- **Employee detail page** (`/employees/:empId`) showing full attendance history.
- **Upload modal**: drag-and-drop or click-to-browse, upload progress bar, validation
  errors surfaced per-row, and a preview of inserted vs. updated records after each
  upload.
- **Dynamic refresh**: after a successful upload, the dashboard and employee table
  refetch automatically — no manual page reload needed.
- **Backend validation & safety**: file type/size checks, per-row error collection
  (bad dates/status/missing IDs don't fail the whole batch), and DB-level unique
  constraints as a second line of defense against duplicates.

---

## 8. API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload an Excel file; returns counts + preview + errors |
| GET | `/api/uploads/history` | Recent upload audit log |
| GET | `/api/summary?date=YYYY-MM-DD` | Dashboard summary counts |
| GET | `/api/chart-data?days=14` | Daily status counts for the trend chart |
| GET | `/api/status-distribution?date=` | Status breakdown for the pie chart |
| GET | `/api/employees?search=&date=&status=` | Employee list with aggregate stats |
| GET | `/api/employees/{emp_id}` | Single employee + full attendance history |
| GET | `/api/attendance?date=&emp_id=&status=` | Raw attendance rows (filterable) |

Full interactive documentation is auto-generated by FastAPI at `/docs`.

---

## 9. Notes for Production Use

- Set `allow_origins` in `backend/app/main.py`'s CORS middleware to your real frontend
  domain instead of `"*"`.
- Consider adding authentication (e.g. JWT) around the upload endpoint since it writes
  to the database — this starter ships without auth so you can wire in your own.
- SQLite is great for small/medium HR teams; for larger organizations swap the
  connection string in `backend/app/database.py` for PostgreSQL/MySQL (SQLAlchemy
  makes this a one-line change plus a driver install).

## ODC Tracker (separate module)

The ODC Tracker is available from the left sidebar at **ODC Tracker**. It is an additive module and stores its data in separate SQLite tables: `odc_employees`, `odc_logs`, and `odc_uploads`; it does not write to or reset the attendance tables.

### Upload workbook
1. Start the backend and frontend using the normal instructions above.
2. Open **ODC Tracker** and choose the Excel workbook.
3. Upload the workbook containing the roster/output table and ODC log/input table. The importer maps common header variants based on column names.
4. Review **Employee reconciliation**, **ODC logs**, and **Upload history**. Use search, location/project filters, and date filters as needed.

The importer normalizes employee IDs, stores distinct log-date identities, and updates repeated log identities on later uploads. Invalid/missing dates are skipped with warnings; `#N/A` worked-from-ODC values are left unknown rather than converted to zero. Check upload warnings after import, especially if your workbook uses unusual header names.

A reusable implementation prompt is included in `ODC_TRACKER_IMPLEMENTATION_PROMPT.md`.
