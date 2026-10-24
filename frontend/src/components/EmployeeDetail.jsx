import React, { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, User, CalendarPlus, Pencil, Trash2 } from 'lucide-react'
import StatusBadge from './StatusBadge.jsx'
import AttendanceFormModal from './AttendanceFormModal.jsx'
import ConfirmDialog from './ConfirmDialog.jsx'
import { getEmployeeDetail, deleteAttendance } from '../api.js'

export default function EmployeeDetail() {
  const { empId } = useParams()
  const [employee, setEmployee] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    return getEmployeeDetail(empId)
      .then((res) => setEmployee(res.data))
      .catch(() => setError('Employee not found or the server is unreachable.'))
      .finally(() => setLoading(false))
  }, [empId])

  useEffect(() => {
    let active = true
    load().then(() => {})
    return () => { active = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empId])

  const counts = React.useMemo(() => {
    const base = { Present: 0, Absent: 0, WFH: 0, Leave: 0, 'Half Day': 0 }
    employee?.attendance?.forEach((r) => { base[r.status] = (base[r.status] || 0) + 1 })
    return base
  }, [employee])

  const openCreate = () => { setEditingRecord(null); setFormOpen(true) }
  const openEdit = (record) => { setEditingRecord(record); setFormOpen(true) }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteAttendance(deleteTarget.id)
      setDeleteTarget(null)
      load()
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to delete attendance record.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="employee-detail">
      <Link to="/" className="back-link"><ArrowLeft size={16} /> Back to dashboard</Link>

      {loading && <div className="chart-placeholder">Loading employee…</div>}
      {error && <div className="alert alert-error page-alert">{error}</div>}

      {employee && !loading && (
        <>
          <div className="employee-header-card">
            <div className="employee-avatar"><User size={28} /></div>
            <div>
              <h2>{employee.name}</h2>
              <p className="mono">{employee.emp_id}</p>
            </div>
          </div>

          <div className="summary-grid employee-stats-grid">
            {Object.entries(counts).map(([status, count]) => (
              <div className="summary-card" key={status}>
                <div className="summary-card-body">
                  <span className="summary-card-value">{count}</span>
                  <span className="summary-card-label">{status}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="table-card">
            <div className="table-card-header">
              <div>
                <h3>Attendance History</h3>
                <span className="chart-subtitle">{employee.attendance.length} records</span>
              </div>
              <button className="primary-btn" onClick={openCreate}>
                <CalendarPlus size={16} /> Add Attendance
              </button>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Check In</th>
                    <th>Check Out</th>
                    <th>Comments</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {employee.attendance.length === 0 ? (
                    <tr><td colSpan={6} className="empty-row">No attendance records yet. Click "Add Attendance" to create one.</td></tr>
                  ) : (
                    employee.attendance.map((r) => (
                      <tr key={r.id}>
                        <td>{r.date}</td>
                        <td><StatusBadge status={r.status} /></td>
                        <td>{r.check_in || '—'}</td>
                        <td>{r.check_out || '—'}</td>
                        <td>{r.comments || '—'}</td>
                        <td className="row-actions">
                          <button className="icon-btn sm" title="Edit" onClick={() => openEdit(r)}>
                            <Pencil size={14} />
                          </button>
                          <button className="icon-btn sm danger" title="Delete" onClick={() => setDeleteTarget(r)}>
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {formOpen && (
        <AttendanceFormModal
          empId={empId}
          record={editingRecord}
          onClose={() => setFormOpen(false)}
          onSuccess={async() => {await load()}}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Delete this attendance record?"
          message={`This removes the ${deleteTarget.status} record for ${deleteTarget.date}. This cannot be undone.`}
          confirmLabel="Delete Record"
          busy={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}