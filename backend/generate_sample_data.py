"""
Generates a sample Excel file (sample_attendance.xlsx) you can use to test
the upload feature. Run: python generate_sample_data.py
"""
import pandas as pd
from datetime import date, timedelta
import random

employees = [
    ("EMP001", "Aarav Sharma"),
    ("EMP002", "Priya Nair"),
    ("EMP003", "Rohan Mehta"),
    ("EMP004", "Sneha Iyer"),
    ("EMP005", "Karthik Raj"),
    ("EMP006", "Ananya Gupta"),
    ("EMP007", "Vikram Singh"),
    ("EMP008", "Divya Menon"),
]

statuses = ["Present", "Present", "Present", "WFH", "Absent", "Leave", "Half Day"]

rows = []
start = date.today() - timedelta(days=13)
for d in range(14):
    current = start + timedelta(days=d)
    if current.weekday() >= 5:
        continue  # skip weekends
    for emp_id, name in employees:
        status = random.choice(statuses)
        check_in = "09:15" if status in ("Present", "Half Day") else ("09:30" if status == "WFH" else "")
        check_out = "18:10" if status == "Present" else ("13:30" if status == "Half Day" else ("18:00" if status == "WFH" else ""))
        rows.append(
            {
                "Emp No": emp_id,
                "Employee Name": name,
                "Date": current.strftime("%Y-%m-%d"),
                "Attendance Status": status,
                "CheckIn": check_in,
                "CheckOut": check_out,
                "Comments": "" if status == "Present" else f"{status} day",
            }
        )

df = pd.DataFrame(rows)
df.to_excel("sample_attendance.xlsx", index=False)
print(f"Generated sample_attendance.xlsx with {len(rows)} rows")
