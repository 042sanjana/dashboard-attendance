# Employee Attendance Dashboard & ODC Tracker
 
A full-stack web application for managing employee attendance and ODC (Office/Onsite/Work-location) tracking. The application allows users to import Excel data, monitor employee attendance, view analytics, track working hours, and manage employee remarks.
 
## Features
 
### 1. Attendance Dashboard
- Import employee attendance data from Excel files.
- View attendance summary cards and status distribution.
- Search and filter employee records.
- View employee-wise attendance history.
- Track Present, Absent, WFH, Leave, and other supported statuses.
- View check-in and check-out timings.
- Calculate working hours when valid timings are available.
- Add, edit, and delete attendance records.
- View Excel upload history and import errors.
 
### 2. Attendance Analytics
- View attendance graphs and reports.
- Filter records by employee, status, month, and year where supported.
- Analyze daily, monthly, and yearly attendance trends.
- Review employee-wise and team-wide working-hours summaries.
- Update analytics automatically when filters change.
 
### 3. ODC Tracker
- Import ODC Tracker information from Excel workbooks.
- View employee details and ODC log records.
- Review ODC summaries and upload history.
- Search and filter available ODC records.
- Edit and save employee remarks.
- Store ODC records separately from attendance data.
 
### 4. Excel Data Processing
- Validate Excel files and required fields.
- Process employee IDs, names, dates, statuses, and timings.
- Identify duplicate employee/date attendance records.
- Update matching attendance records during repeated imports.
- Report invalid rows and import warnings.
 
## Technology Stack
 
| Component | Technologies |
|---|---|
| Frontend | React.js, Vite |
| Routing | React Router |
| Charts | Recharts |
| Icons | Lucide React |
| API Requests | Axios |
| Backend | Python, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data Processing | Pandas, OpenPyXL |
| API Documentation | Swagger UI |
 
## Project Structure
 
```text
dashboard-attendance-main/
├── README.md
├── ODC_TRACKER_IMPLEMENTATION_PROMPT.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── excel_processor.py
│   │   ├── analytics.py
│   │   └── odc_tracker.py
│   ├── requirements.txt
│   ├── generate_sample_data.py
│   ├── ODC_Tracker_Import_Template.xlsx
│   ├── Sample_Attendance_Dashboard_Data.xlsx
│   └── sample_attendance.xlsx
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── main.jsx
│       ├── index.css
│       ├── timing.js
│       └── components/
│           ├── AnalyticsPanel.jsx
│           ├── AttendanceFormModal.jsx
│           ├── AttendanceTrendChart.jsx
│           ├── ConfirmDialog.jsx
│           ├── Dashboard.jsx
│           ├── EmployeeDetail.jsx
│           ├── EmployeeFormModal.jsx
│           ├── EmployeeTable.jsx
│           ├── ODCTracker.css
│           ├── ODCTracker.jsx
│           ├── ResetDataButton.jsx
│           ├── Sidebar.jsx
│           ├── StatusBadge.jsx
│           ├── StatusPieChart.jsx
│           ├── SummaryCards.jsx
│           ├── Topbar.jsx
│           └── UploadModal.jsx
└── uploads/
```
 
*The structure above describes the main project files. Local upload files and generated files may vary.*
 
## Prerequisites
 
Install the following before running the application:
 
- Python 3.10 or later
- Node.js 18 or later
- npm
- Visual Studio Code or another code editor
 
Check your installed versions:
 
```bash
python --version
node --version
npm --version
```
 
## Installation and Setup
 
Run the backend and frontend in separate terminals.
 
### Step 1: Clone the Repository
 
If you are downloading the project from GitHub:
 
```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd dashboard-attendance-main
```
 
Replace the placeholder with your actual repository URL.
 
If the project is already extracted on your computer, simply open the project folder in VS Code.
 
### Step 2: Set Up the Backend
 
Open a terminal in the project root and run:
 
**Windows PowerShell:**
 
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
 
If you use Windows Command Prompt, activate the environment with:
 
```bat
venv\Scripts\activate.bat
```
 
**macOS/Linux:**
 
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
 
The backend runs at:
 
- API: http://localhost:8000
- Swagger API documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc
- Health check: http://localhost:8000/api/health
 
Keep the backend terminal running.
 
### Step 3: Set Up the Frontend
 
Open a second terminal in the project root:
 
```bash
cd frontend
npm install
npm run dev
```
 
Open the local URL printed by Vite, usually:
 
http://localhost:5173
 
Keep the frontend terminal running while using the application.
 
### Step 4: Build the Frontend
 
To create a production build:
 
```bash
cd frontend
npm run build
```
 
The generated build is normally available in `frontend/dist/`.
 
## Importing Attendance Excel Data
 
1. Start the backend and frontend.
2. Open the application in your browser.
3. Navigate to the Attendance Dashboard.
4. Select the Excel upload option.
5. Choose the attendance workbook.
6. Upload the file and review the import result.
7. Verify the dashboard cards, employee records, and charts.
 
### Typical Attendance Columns
 
| Column | Example |
|---|---|
| Employee ID | EMP001 |
| Employee Name | Aarav Sharma |
| Date | 2026-09-23 |
| Attendance Status | Present |
| Check-in Time | 09:15 |
| Check-out Time | 18:10 |
| Comments | Worked from office |
 
Use the supplied sample workbook as the primary reference for supported column names and formats.
 
Common statuses include Present, Absent, WFH, Leave, and Half Day, depending on the importer configuration.
 
### Duplicate Records
 
Attendance records are identified using employee ID and attendance date. Re-importing an existing employee/date record is intended to update the matching record rather than create a duplicate. Records for other dates are retained.
 
Invalid rows may be skipped and reported in the upload response.
 
## Using the ODC Tracker
 
1. Open the ODC Tracker from the application sidebar.
2. Select the ODC Excel workbook.
3. Upload the workbook.
4. Review the ODC summary, logs, and upload history.
5. Search and filter records using the available options.
6. Edit remarks where the application provides an editable field.
7. Verify that changes are saved successfully.
 
Use `backend/ODC_Tracker_Import_Template.xlsx` as a reference for the expected workbook format.
 
ODC data is managed separately from attendance data.
 
## Attendance and Working-Hours Analytics
 
The analytics module provides attendance graph data, filtered daily records, and working-hours summaries.
 
Available analytics depend on the records imported into the database and the filters supported by the application.
 
Working hours can only be calculated when valid check-in and check-out times are available. Missing or invalid times should be checked against the original Excel workbook.
 
## API Endpoints
 
The FastAPI backend provides REST APIs for attendance management, analytics, and ODC tracking.
 
### General and Attendance APIs
 
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend status |
| POST | `/api/upload` | Upload attendance Excel data |
| GET | `/api/uploads/history` | View attendance upload history |
| GET | `/api/summary` | Retrieve dashboard summary |
| GET | `/api/chart-data` | Retrieve attendance chart data |
| GET | `/api/status-distribution` | Retrieve status distribution |
| GET | `/api/employees` | List or filter employees |
| GET | `/api/employees/{emp_id}` | Retrieve employee details |
| POST | `/api/employees` | Create an employee |
| PUT | `/api/employees/{emp_id}` | Update an employee |
| DELETE | `/api/employees/{emp_id}` | Delete an employee |
| GET | `/api/attendance` | Retrieve attendance records |
| POST | `/api/attendance` | Create an attendance record |
| PUT | `/api/attendance/{record_id}` | Update an attendance record |
| DELETE | `/api/attendance/{record_id}` | Delete an attendance record |
| POST | `/api/reset` | Reset attendance data |
| DELETE | `/api/reset` | Reset attendance data |
 
### Analytics APIs
 
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/analytics/filters` | Retrieve analytics filters |
| GET | `/api/analytics/attendance-graph` | Retrieve attendance graph data |
| GET | `/api/analytics/daily-records` | Retrieve filtered daily records |
| GET | `/api/analytics/working-hours` | Retrieve working-hours analytics |
 
### ODC Tracker APIs
 
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/odc/upload` | Upload ODC workbook |
| GET | `/api/odc/summary` | Retrieve ODC summary |
| GET | `/api/odc/logs` | Retrieve ODC logs |
| GET | `/api/odc/uploads` | Retrieve ODC upload history |
| PUT | `/api/odc/employees/{emp_id}/remarks` | Update ODC employee remarks |
 
**Note:** Confirm the exact endpoint paths, HTTP methods, and parameters in the running API documentation at http://localhost:8000/docs. The table summarizes the project's intended API functions.
 
## Database
 
The application uses SQLite for local data storage.
 
Important backend files:
 
- `database.py` — database connection and configuration.
- `models.py` — database models.
- `schemas.py` — request and response schemas.
- `excel_processor.py` — attendance Excel processing.
- `analytics.py` — attendance and working-hours analytics.
- `odc_tracker.py` — ODC Tracker functionality.
- `main.py` — FastAPI application and route configuration.
 
Back up your database before resetting data or changing database schemas.
