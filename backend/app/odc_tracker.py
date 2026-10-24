"""Isolated ODC Tracker API. Uses separate tables; never mutates attendance tables."""
from datetime import datetime, date
from io import BytesIO
import json, re
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Body
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, UniqueConstraint, func
from sqlalchemy.orm import Session
from sqlalchemy.sql import func as sqlfunc
from .database import Base, get_db

router = APIRouter(prefix="/api/odc", tags=["ODC Tracker"])

class ODCEmployee(Base):
    __tablename__ = "odc_employees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(80), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=True)
    location = Column(String(100), nullable=True)
    project_name = Column(String(250), nullable=True)
    pm_name = Column(String(200), nullable=True)
    worked_from_odc = Column(Integer, nullable=True)
    remarks = Column(Text, nullable=True)
    source_status = Column(String(80), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ODCEmployeeRemark(Base):
    """User-edited remarks, kept separate so Excel imports cannot overwrite them."""
    __tablename__ = "odc_employee_remarks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(80), unique=True, index=True, nullable=False)
    remarks = Column(Text, nullable=False, default='')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ODCLog(Base):
    __tablename__ = "odc_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(80), index=True, nullable=False)
    emp_name = Column(String(200), nullable=True)
    lob = Column(String(200), nullable=True)
    dm_name = Column(String(200), nullable=True)
    log_date = Column(Date, nullable=True, index=True)
    work_count = Column(String(80), nullable=True)
    upload_id = Column(Integer, nullable=True, index=True)
    raw_json = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint('emp_id', 'log_date', 'lob', 'dm_name', name='uq_odc_log_identity'),)

class ODCUpload(Base):
    __tablename__ = "odc_uploads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    total_rows = Column(Integer, default=0)
    inserted_logs = Column(Integer, default=0)
    updated_employees = Column(Integer, default=0)
    unmatched_logs = Column(Integer, default=0)
    errors_json = Column(Text, nullable=True)

def norm_id(v):
    if pd.isna(v): return ''
    s = str(v).strip()
    if s.endswith('.0'): s = s[:-2]
    return re.sub(r'\s+', '', s).upper()

def norm_header(v):
    return re.sub(r'[^a-z0-9]+', '', str(v).lower())
def pick(row, *names):
    keys = {norm_header(k): k for k in row.index}
    for n in names:
        if norm_header(n) in keys: return row[keys[norm_header(n)]]
    for k in row.index:
        nk = norm_header(k)
        if any(norm_header(n) in nk for n in names): return row[k]
    return None
def clean(v):
    if v is None or pd.isna(v): return None
    s = str(v).strip()
    return None if s.lower() in ('nan','none','nat','') else s

def as_date(v):
    if v is None or pd.isna(v): return None
    try: return pd.to_datetime(v, errors='raise').date()
    except Exception: return None

@router.post('/upload')
async def upload_odc(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(('.xlsx', '.xlsm', '.xls')):
        raise HTTPException(400, 'Upload an Excel workbook (.xlsx or .xls).')
    try:
        content = await file.read()
        book = pd.ExcelFile(BytesIO(content))
        raw_sheets = {str(s).strip().lower(): pd.read_excel(BytesIO(content), sheet_name=s, header=None, dtype=object) for s in book.sheet_names}
    except Exception as e:
        raise HTTPException(400, f'Could not read workbook: {e}')
    # The reference workbook may contain BOTH logical tables vertically on Sheet1.
    # Find each header row independently rather than assuming one header per worksheet.
    master_df = logs_df = None
    for raw_df in raw_sheets.values():
        header_rows=[]
        for ridx, row in raw_df.iterrows():
            vals=[norm_header(v) for v in row.tolist() if v is not None and not pd.isna(v)]
            joined=' '.join(vals)
            has_id=any(v in ('empid','mphasisempid','employeeid') for v in vals)
            has_name=any(v in ('empname','ftcname','employeename') for v in vals)
            is_log=has_id and has_name and any(('lob' in v) for v in vals) and any(('date' in v or 'worked' in v) for v in vals)
            is_master=has_id and any(v in ('ftcname','employeename','empname') for v in vals) and (any('ftclocation' in v for v in vals) or any('projectname' in v for v in vals))
            if is_log or is_master:
                header_rows.append((ridx, 'logs' if is_log else 'master', row.tolist()))
        for idx, (header_idx, kind, header) in enumerate(header_rows):
            cols=[]; seen={}
            for cidx, val in enumerate(header):
                label=clean(val) or f'Unnamed_{cidx}'
                seen[label]=seen.get(label,0)+1
                if seen[label]>1: label=f'{label}_{seen[label]}'
                cols.append(label)
            end_idx=header_rows[idx+1][0] if idx+1<len(header_rows) else len(raw_df)
            block=raw_df.iloc[header_idx+1:end_idx].copy()
            block.columns=cols
            block=block.dropna(how='all')
            if kind=='master' and master_df is None: master_df=block
            if kind=='logs' and logs_df is None: logs_df=block
    if master_df is None: master_df = pd.DataFrame()
    if logs_df is None: raise HTTPException(400, 'Could not identify the ODC log table. Expected headers similar to Emp ID, Emp Name, LOB, DM Name, and Date - Worked.')
    upload = ODCUpload(filename=file.filename, total_rows=int(len(logs_df)))
    db.add(upload); db.flush()
    errors=[]; inserted=0; updated=0; unmatched=0
    # Master roster is upserted only into ODC-specific table.
    master_ids=set()
    for _, r in master_df.iterrows():
        emp_id=norm_id(pick(r,'Mphasis EMP ID','Emp ID','Employee ID'))
        if not emp_id: continue
        master_ids.add(emp_id)
        obj=db.query(ODCEmployee).filter_by(emp_id=emp_id).first()
        if not obj: obj=ODCEmployee(emp_id=emp_id); db.add(obj)
        obj.name=clean(pick(r,'FTC Name','Emp Name','Employee Name')) or obj.name
        obj.location=clean(pick(r,'FTC Location','Location')) or obj.location
        obj.project_name=clean(pick(r,'JPMC Project Name where FTC Tagged','JPMC Project Name','Project Name')) or obj.project_name
        obj.pm_name=clean(pick(r,'Mphasis India PM','PM Name')) or obj.pm_name
        worked=clean(pick(r,'Worked from ODC'))
        if worked and worked.lower() not in ('#n/a','n/a','na'): 
            try: obj.worked_from_odc=int(float(worked))
            except ValueError: pass
        # Keep the Excel-provided remark as the source value. Any user-edited remark
        # is stored separately in ODCEmployeeRemark and takes precedence in the UI.
        obj.source_status='Present in roster'
        updated+=1
    db.flush()
    for _, r in logs_df.iterrows():
        emp_id=norm_id(pick(r,'Emp ID','Mphasis EMP ID','Employee ID'))
        if not emp_id: errors.append(f'Row with missing employee ID skipped'); continue
        log_date=as_date(pick(r,'Date - Worked','Date','Work Date','Log Date'))
        if not log_date:
            # Keep rows even when date parsing fails; raw row is available in upload diagnostics.
            errors.append(f'Employee {emp_id}: missing/invalid date; raw row skipped'); continue
        emp_name=clean(pick(r,'Emp Name','FTC Name','Employee Name'))
        lob=clean(pick(r,'LOB'))
        dm=clean(pick(r,'DM Name'))
        count=clean(pick(r,'Work Count','Count','Hours'))
        raw={str(k): (None if pd.isna(v) else str(v)) for k,v in r.to_dict().items()}
        existing=db.query(ODCLog).filter_by(emp_id=emp_id,log_date=log_date,lob=lob,dm_name=dm).first()
        if existing:
            existing.emp_name=emp_name or existing.emp_name; existing.work_count=count or existing.work_count
            existing.raw_json=json.dumps(raw); existing.upload_id=upload.id
        else:
            db.add(ODCLog(emp_id=emp_id,emp_name=emp_name,lob=lob,dm_name=dm,log_date=log_date,work_count=count,upload_id=upload.id,raw_json=json.dumps(raw))); inserted+=1
        if master_ids and emp_id not in master_ids and not db.query(ODCEmployee).filter_by(emp_id=emp_id).first(): unmatched+=1
    upload.inserted_logs=inserted; upload.updated_employees=updated; upload.unmatched_logs=unmatched; upload.errors_json=json.dumps(errors)
    db.commit()
    return {'message':'ODC workbook processed successfully','upload_id':upload.id,'filename':file.filename,'log_rows':len(logs_df),'inserted_logs':inserted,'roster_rows_upserted':updated,'unmatched_log_ids':unmatched,'errors':errors[:100]}

@router.get('/summary')
def summary(search: str = '', location: str = '', project: str = '', db: Session = Depends(get_db)):
    employees=db.query(ODCEmployee).all()
    log_counts={}
    for emp_id, n in db.query(ODCLog.emp_id, func.count(func.distinct(ODCLog.log_date))).group_by(ODCLog.emp_id).all(): log_counts[emp_id]=n
    # Manual remarks override the imported Excel remarks, including an intentional blank.
    manual_remarks={r.emp_id: r.remarks for r in db.query(ODCEmployeeRemark).all()}
    rows=[]
    for e in employees:
        if search and search.lower() not in (e.emp_id+' '+(e.name or '')).lower(): continue
        if location and location.lower() not in (e.location or '').lower(): continue
        if project and project.lower() not in (e.project_name or '').lower(): continue
        rows.append({'emp_id':e.emp_id,'name':e.name,'location':e.location,'project_name':e.project_name,'pm_name':e.pm_name,'worked_from_odc':e.worked_from_odc,'distinct_log_days':log_counts.get(e.emp_id,0),'remarks':manual_remarks[e.emp_id] if e.emp_id in manual_remarks else e.remarks,'source_status':e.source_status})
    return {'total_employees':len(employees),'total_log_rows':db.query(ODCLog).count(),'matched_employees':sum(1 for r in rows if r['distinct_log_days']>0),'employees':rows}

@router.put('/employees/{emp_id}/remarks')
def update_employee_remarks(emp_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Save editable employee remarks in the ODC-only database table."""
    normalized_id = norm_id(emp_id)
    if not normalized_id:
        raise HTTPException(status_code=400, detail='A valid employee ID is required.')
    if not isinstance(payload, dict) or 'remarks' not in payload:
        raise HTTPException(status_code=422, detail='Request body must include a remarks field.')
    value = payload.get('remarks')
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail='Remarks must be text.')
    value = value.strip()
    if len(value) > 2000:
        raise HTTPException(status_code=422, detail='Remarks must be 2000 characters or fewer.')
    employee = db.query(ODCEmployee).filter_by(emp_id=normalized_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail='Employee not found in the ODC roster.')
    manual = db.query(ODCEmployeeRemark).filter_by(emp_id=normalized_id).first()
    if manual is None:
        manual = ODCEmployeeRemark(emp_id=normalized_id, remarks=value)
        db.add(manual)
    else:
        manual.remarks = value
        manual.updated_at = datetime.utcnow()
    db.commit()
    return {'message': 'Remarks saved successfully.', 'emp_id': employee.emp_id, 'remarks': manual.remarks}


@router.get('/logs')
def logs(emp_id: str = '', start_date: date = None, end_date: date = None, db: Session = Depends(get_db)):
    q=db.query(ODCLog)
    if emp_id: q=q.filter(ODCLog.emp_id==norm_id(emp_id))
    if start_date: q=q.filter(ODCLog.log_date>=start_date)
    if end_date: q=q.filter(ODCLog.log_date<=end_date)
    return [{'id':x.id,'emp_id':x.emp_id,'emp_name':x.emp_name,'lob':x.lob,'dm_name':x.dm_name,'log_date':x.log_date.isoformat() if x.log_date else None,'work_count':x.work_count,'raw':json.loads(x.raw_json) if x.raw_json else {}} for x in q.order_by(ODCLog.log_date.desc()).limit(5000).all()]

@router.get('/uploads')
def uploads(db: Session = Depends(get_db)):
    return [{'id':x.id,'filename':x.filename,'uploaded_at':x.uploaded_at.isoformat() if x.uploaded_at else None,'total_rows':x.total_rows,'inserted_logs':x.inserted_logs,'updated_employees':x.updated_employees,'unmatched_logs':x.unmatched_logs,'errors':json.loads(x.errors_json or '[]')} for x in db.query(ODCUpload).order_by(ODCUpload.id.desc()).limit(50).all()]
