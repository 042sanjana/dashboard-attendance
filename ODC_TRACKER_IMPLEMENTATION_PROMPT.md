# Prompt to build/extend the ODC Tracker module

You are extending an existing Attendance Dashboard codebase built with React + Vite on the frontend and FastAPI + SQLAlchemy + SQLite on the backend. Add a separate sidebar module named **ODC Tracker**. Do not rebuild the app from scratch and do not change, delete, reset, rename, or migrate the existing attendance tables, APIs, Excel import behavior, routes, UI, or data.

Use the supplied workbook screenshots as the business reference. The workbook has an ODC log/input table with columns similar to `Emp ID`, `Emp Name`, `LOB`, `DM Name`, `Date - Worked`, and `Work Count`; and a roster/output table with columns similar to `Mphasis EMP ID`, `FTC Name`, `FTC Location (HYD/BAN/MUM/PUNE/US)`, `JPMC Project Name where FTC Tagged`, `Mphasis India PM`, `Worked from ODC`, and `Comments/Remarks`. Headers may vary slightly, so normalize header names and match columns flexibly. Employee IDs may appear as numeric values or strings; normalize them without losing digits or leading zeros when the source provides them as text.

Implement these requirements:
1. Add a distinct `ODC Tracker` sidebar item and route/page inside the existing app. Keep the current Attendance Dashboard page and styling/functionality working.
2. Add isolated SQLAlchemy tables named `odc_employees`, `odc_logs`, and `odc_uploads`. Never use attendance tables to store ODC data. Do not reset the database on startup.
3. Upload Excel workbooks with two logical tables/sheets. Identify roster and raw-log tables from headers, not only sheet names. Validate the file and report understandable errors.
4. Upsert roster records by normalized employee ID. Retain raw date-level ODC logs. Count distinct log dates per employee, not duplicate rows. Make repeat uploads idempotent: duplicate employee/date/LOB/DM records should update rather than duplicate.
5. Display roster fields, number of distinct ODC log days, remarks/comments, and a visible state for employees with no matching logs. Keep `#N/A`, missing IDs, invalid dates, and unmatched IDs visible in upload diagnostics rather than inventing data. Preserve remarks such as `Not logged into ODC` and `Asked to Ignore - Prod Support - JPMC (T&M)`.
6. Include search by employee name/ID; filters by location and JPMC project; an ODC log table filterable by employee ID and date range; upload history with row counts, unmatched IDs, and warnings.
7. Provide FastAPI routes under `/api/odc` for upload, summary, logs, and upload history. Use the existing API client/proxy conventions.
8. Use a clean responsive UI consistent with the existing HR Portal. Include loading/error/success states and empty states. All controls must work.
9. Update the README with setup and usage. Do not introduce external paid APIs or unnecessary dependencies.
10. Validate Python syntax and run the frontend production build. If a workbook structure cannot be confidently mapped, show a useful validation error instead of silently mapping wrong columns.

Deliver the complete changed project, preserve all existing files/features, and include a concise list of changed files plus exact run instructions.
