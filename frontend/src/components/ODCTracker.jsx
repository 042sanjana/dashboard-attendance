import React, { useEffect, useMemo, useState } from 'react'
import { Search, UploadCloud, Users, CalendarDays, AlertTriangle, RefreshCw, FileSpreadsheet, Pencil, Save, X, LoaderCircle } from 'lucide-react'
import api from '../api.js'
import './ODCTracker.css'

export default function ODCTracker() {
  const [summary, setSummary] = useState({ employees: [], total_employees: 0, total_log_rows: 0, matched_employees: 0 })
  const [logs, setLogs] = useState([])
  const [uploads, setUploads] = useState([])
  const [search, setSearch] = useState('')
  const [location, setLocation] = useState('')
  const [project, setProject] = useState('')
  const [selectedEmp, setSelectedEmp] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [tab, setTab] = useState('roster')
  const [editingEmp, setEditingEmp] = useState('')
  const [editRemark, setEditRemark] = useState('')
  const [savingRemark, setSavingRemark] = useState(false)

  async function load() {
    try {
      const [s, l, u] = await Promise.all([
        api.get('/odc/summary', { params: { search, location, project } }),
        api.get('/odc/logs', { params: { emp_id: selectedEmp, start_date: startDate || undefined, end_date: endDate || undefined } }),
        api.get('/odc/uploads'),
      ])
      setSummary(s.data); setLogs(l.data); setUploads(u.data); setError('')
    } catch (e) { setError(e.response?.data?.detail || 'Could not load ODC data. Check that the FastAPI backend is running.') }
  }
  useEffect(() => { load() }, [search, location, project, selectedEmp, startDate, endDate])

  const locations = useMemo(() => [...new Set((summary.employees || []).map(x => x.location).filter(Boolean))].sort(), [summary.employees])
  const projects = useMemo(() => [...new Set((summary.employees || []).map(x => x.project_name).filter(Boolean))].sort(), [summary.employees])
  function startEditingRemark(employee) {
    setEditingEmp(employee.emp_id)
    setEditRemark(employee.remarks || '')
    setError('')
    setMessage('')
  }

  function cancelEditingRemark() {
    setEditingEmp('')
    setEditRemark('')
  }

  async function saveRemark(empId) {
    setSavingRemark(true)
    setError('')
    setMessage('')
    try {
      await api.put(`/odc/employees/${encodeURIComponent(empId)}/remarks`, { remarks: editRemark })
      setMessage(`Remarks saved for employee ${empId}.`)
      setEditingEmp('')
      setEditRemark('')
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save remarks. Please try again.')
    } finally {
      setSavingRemark(false)
    }
  }

  async function upload() {
    if (!file) { setError('Choose the ODC Excel workbook first.'); return }
    const data = new FormData(); data.append('file', file)
    setBusy(true); setError(''); setMessage('')
    try {
      const res = await api.post('/odc/upload', data, { headers: { 'Content-Type': 'multipart/form-data' } })
      setMessage(`Upload complete: ${res.data.inserted_logs} new log rows, ${res.data.roster_rows_upserted} roster rows processed, ${res.data.unmatched_log_ids} unmatched IDs.`)
      setFile(null); document.getElementById('odc-file-input')?.value && (document.getElementById('odc-file-input').value = '')
      await load()
    } catch (e) { setError(e.response?.data?.detail || 'Upload failed. Check workbook columns and try again.') }
    finally { setBusy(false) }
  }
  return <div className="odc-page">
    <div className="odc-heading"><div><div className="odc-eyebrow">HR PORTAL / OPERATIONS</div><h1>ODC Tracker</h1><p>Reconcile ODC access logs with the employee roster, track distinct working dates, and review exceptions.</p></div><button className="odc-refresh" onClick={load}><RefreshCw size={16}/> Refresh</button></div>
    {error && <div className="odc-alert error"><AlertTriangle size={17}/>{error}</div>}{message && <div className="odc-alert success">{message}</div>}
    <div className="odc-upload-panel"><div className="odc-upload-icon"><FileSpreadsheet size={22}/></div><div className="odc-upload-copy"><strong>Import ODC workbook</strong><span>Upload the Excel file containing the ODC logs and employee roster/output table. Existing ODC records are updated safely; attendance records are untouched.</span></div><input id="odc-file-input" type="file" accept=".xlsx,.xls,.xlsm" onChange={e => setFile(e.target.files?.[0] || null)}/><button disabled={busy || !file} onClick={upload}><UploadCloud size={16}/>{busy ? 'Processing…' : 'Upload & Reconcile'}</button></div>
    <div className="odc-metrics"><div className="odc-metric"><span><Users size={17}/> Roster employees</span><strong>{summary.total_employees ?? 0}</strong><small>Unique normalized employee IDs</small></div><div className="odc-metric"><span><FileSpreadsheet size={17}/> ODC log rows</span><strong>{summary.total_log_rows ?? 0}</strong><small>Raw date-level records retained</small></div><div className="odc-metric"><span><CalendarDays size={17}/> Matched employees</span><strong>{summary.matched_employees ?? 0}</strong><small>Roster employees with log dates</small></div><div className="odc-metric"><span><AlertTriangle size={17}/> Latest uploads</span><strong>{uploads.length}</strong><small>Upload history available below</small></div></div>
    <div className="odc-filters"><div className="odc-search"><Search size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search employee name or ID…"/></div><select value={location} onChange={e => setLocation(e.target.value)}><option value="">All locations</option>{locations.map(x => <option key={x}>{x}</option>)}</select><select value={project} onChange={e => setProject(e.target.value)}><option value="">All projects</option>{projects.map(x => <option key={x}>{x}</option>)}</select></div>
    <div className="odc-tabs"><button className={tab==='roster'?'active':''} onClick={()=>setTab('roster')}>Employee reconciliation</button><button className={tab==='logs'?'active':''} onClick={()=>setTab('logs')}>ODC logs</button><button className={tab==='uploads'?'active':''} onClick={()=>setTab('uploads')}>Upload history</button></div>
    {tab === 'roster' && <div className="odc-table-wrap"><table className="odc-table"><thead><tr><th>Mphasis EMP ID</th><th>FTC Name</th><th>FTC Location</th><th>JPMC Project</th><th>Mphasis India PM</th><th>Worked from ODC</th><th>Distinct log days</th><th>Remarks / Comments</th></tr></thead><tbody>{summary.employees.map(e=><tr key={e.emp_id}><td className="odc-id">{e.emp_id}</td><td>{e.name || '—'}</td><td>{e.location || '—'}</td><td>{e.project_name || '—'}</td><td>{e.pm_name || '—'}</td><td>{e.worked_from_odc ?? '—'}</td><td><span className={e.distinct_log_days ? 'odc-count good' : 'odc-count'}>{e.distinct_log_days}</span></td><td className="odc-remarks-cell">{editingEmp === e.emp_id ? <div className="odc-remark-editor"><textarea aria-label={`Remarks for ${e.emp_id}`} maxLength={2000} value={editRemark} onChange={event => setEditRemark(event.target.value)} placeholder="Enter comments or remarks…" rows={3} /><div className="odc-remark-actions"><button type="button" className="odc-save-remark" onClick={() => saveRemark(e.emp_id)} disabled={savingRemark}>{savingRemark ? <LoaderCircle size={14} className="odc-spin"/> : <Save size={14}/>}Save</button><button type="button" className="odc-cancel-remark" onClick={cancelEditingRemark} disabled={savingRemark}><X size={14}/>Cancel</button></div></div> : <div className="odc-remark-display"><span>{e.remarks || (e.distinct_log_days ? '—' : <span className="odc-muted">No matching ODC logs</span>)}</span><button type="button" className="odc-edit-remark" title={`Edit remarks for ${e.emp_id}`} aria-label={`Edit remarks for ${e.emp_id}`} onClick={() => startEditingRemark(e)}><Pencil size={14}/>Edit</button></div>}</td></tr>)}{!summary.employees.length && <tr><td colSpan="8" className="odc-empty">No roster data yet. Upload your ODC workbook to begin.</td></tr>}</tbody></table></div>}
    {tab === 'logs' && <><div className="odc-log-filters"><label>Employee ID<select value={selectedEmp} onChange={e=>setSelectedEmp(e.target.value)}><option value="">All employees</option>{summary.employees.map(e=><option key={e.emp_id} value={e.emp_id}>{e.emp_id} — {e.name || 'Unknown'}</option>)}</select></label><label>From<input type="date" value={startDate} onChange={e=>setStartDate(e.target.value)}/></label><label>To<input type="date" value={endDate} onChange={e=>setEndDate(e.target.value)}/></label><button onClick={()=>{setSelectedEmp('');setStartDate('');setEndDate('')}}>Clear filters</button></div><div className="odc-table-wrap"><table className="odc-table"><thead><tr><th>Emp ID</th><th>Employee name</th><th>LOB</th><th>DM Name</th><th>Log date</th><th>Work count</th></tr></thead><tbody>{logs.map(l=><tr key={l.id}><td className="odc-id">{l.emp_id}</td><td>{l.emp_name||'—'}</td><td>{l.lob||'—'}</td><td>{l.dm_name||'—'}</td><td>{l.log_date||'—'}</td><td>{l.work_count||'—'}</td></tr>)}{!logs.length&&<tr><td colSpan="6" className="odc-empty">No ODC log records match these filters.</td></tr>}</tbody></table></div></>}
    {tab === 'uploads' && <div className="odc-table-wrap"><table className="odc-table"><thead><tr><th>Upload ID</th><th>Filename</th><th>Uploaded at</th><th>Input rows</th><th>New log rows</th><th>Roster rows processed</th><th>Unmatched IDs</th><th>Warnings</th></tr></thead><tbody>{uploads.map(u=><tr key={u.id}><td>{u.id}</td><td>{u.filename}</td><td>{u.uploaded_at ? new Date(u.uploaded_at).toLocaleString() : '—'}</td><td>{u.total_rows}</td><td>{u.inserted_logs}</td><td>{u.updated_employees}</td><td>{u.unmatched_logs}</td><td>{u.errors?.length || 0}</td></tr>)}{!uploads.length&&<tr><td colSpan="8" className="odc-empty">No uploads recorded yet.</td></tr>}</tbody></table>{uploads.some(u=>u.errors?.length) && <div className="odc-warnings"><strong>Recent upload warnings</strong>{uploads.filter(u=>u.errors?.length).slice(0,3).map(u=><div key={u.id}><b>{u.filename}</b><ul>{u.errors.slice(0,8).map((x,i)=><li key={i}>{x}</li>)}</ul></div>)}</div>}</div>}
    <p className="odc-footnote">Data integrity: ODC records use separate <code>odc_employees</code>, <code>odc_logs</code>, and <code>odc_uploads</code> tables. Uploads never reset or modify attendance data. Duplicate log identities are upserted rather than duplicated.</p>
  </div>
}
