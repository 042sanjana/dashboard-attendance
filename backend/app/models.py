"""
SQLAlchemy ORM models.

- Employee: emp_id is the unique primary key. Duplicate employees (same
  emp_id) are never re-inserted; only their name is refreshed if changed.
- Attendance: one row per employee per date, enforced with a UNIQUE
  constraint on (emp_id, date). Re-uploading a file with the same
  emp_id + date UPDATES the existing row instead of creating a duplicate,
  so full attendance history is preserved and never duplicated.
- UploadLog: keeps an audit trail of every Excel upload (for the
  "preview of inserted/updated records" requirement and error history).
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    Time,
    Text,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Employee(Base):
    __tablename__ = "employees"

    emp_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    attendance_records = relationship(
        "Attendance",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="Attendance.date.desc()",
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(50), ForeignKey("employees.emp_id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="Absent")
    check_in = Column(Time, nullable=True)
    check_out = Column(Time, nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", back_populates="attendance_records")

    __table_args__ = (
        UniqueConstraint("emp_id", "date", name="uq_emp_date"),
        Index("ix_attendance_emp_date", "emp_id", "date"),
    )


class UploadLog(Base):
    __tablename__ = "upload_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    total_rows = Column(Integer, default=0)
    new_employees = Column(Integer, default=0)
    inserted_attendance = Column(Integer, default=0)
    updated_attendance = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    errors_json = Column(Text, nullable=True)
