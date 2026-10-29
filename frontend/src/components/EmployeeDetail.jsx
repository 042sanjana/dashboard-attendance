import React, { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, User, CalendarPlus, Pencil, Trash2 } from 'lucide-react'
import StatusBadge from './StatusBadge.jsx'
import AttendanceFormModal from './AttendanceFormModal.jsx'
import ConfirmDialog from './ConfirmDialog.jsx'
import { getEmployeeDetail, deleteAttendance } from '../api.js'
import { TIMING_ORDER, TIMING_META, getTimingCategory } from '../timing.js'

export default function EmployeeDetail() {
  const { empId } = useParams()
  const [employee, setEmployee] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  // click-to-filter; both can be active together
  const [statusFilter, setStatusFilter] = useState(null)
  const [timingFilter, setTimingFilter] = useState(null)

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

  // Status counts always cover all records (they are the status filter itself).
  const counts = React.useMemo(() => {
    const base = { Present: 0, Absent: 0, WFH: 0, Leave: 0, 'Half Day': 0 }
    employee?.attendance?.forEach((r) => { base[r.status] = (base[r.status] || 0) + 1 })
    return base
  }, [employee])

  // Timing counts respect the active status filter, so card numbers match the table.
  const timingCounts = React.useMemo(() => {
    const base = { complete: 0, both_missing: 0, either_missing: 0, invalid: 0 }
    employee?.attendance?.forEach((r) => {
      if (statusFilter && r.status !== statusFilter) return
      base[getTimingCategory(r)] += 1
    })
    return base
  }, [employee, statusFilter])

  const visibleRecords = React.useMemo(() => {
    const all = employee?.attendance || []
    return all.filter((r) => {
      if (statusFilter && r.status !== statusFilter) return false
      if (timingFilter && getTimingCategory(r) !== timingFilter) return false
      return true
    })
  }, [employee, statusFilter, timingFilter])

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

  const filtersActive = Boolean(statusFilter || timingFilter)

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
            {Object.entries(counts).map(([status, count]) => {
              const active = statusFilter === status
              const toggle = () => setStatusFilter(active ? null : status)
              return (
                <div
                  className={`summary-card clickable-card${active ? ' is-active' : ''}`}
                  key={status}
                  role="button"
                  tabIndex={0}
                  aria-pressed={active}
                  title={`Show only ${status} records`}
                  onClick={toggle}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle() }
                  }}
                >
                  <div className="summary-card-body">
                    <span className="summary-card-value">{count}</span>
                    <span className="summary-card-label">{status}</span>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="table-card">
            <div className="table-card-header">
              <div>
                <h3>Attendance History</h3>
                <span className="chart-subtitle">
                  {filtersActive
                    ? `${visibleRecords.length} of ${employee.attendance.length} records`
                    : `${employee.attendance.length} records`}
                </span>
              </div>
              <button className="primary-btn" onClick={openCreate}>
                <CalendarPlus size={16} /> Add Attendance
              </button>
            </div>

            {/* Check-in / check-out colour legend (click to filter) */}
            <div className="tm-legend">
              {TIMING_ORDER.map((key) => {
                const active = timingFilter === key
                return (
                  <button
                    key={key}
                    type="button"
                    aria-pressed={active}
                    title={TIMING_META[key].hint}
                    className={`tm-chip tm-${key}${active ? ' active' : ''}`}
                    onClick={() => setTimingFilter(active ? null : key)}
                  >
                    {TIMING_META[key].label}
                    <strong>{timingCounts[key]}</strong>
                  </button>
                )
              })}
              {filtersActive && (
                <button
                  type="button"
                  className="tm-clear"
                  onClick={() => { setStatusFilter(null); setTimingFilter(null) }}
                >
                  Clear filters
                </button>
              )}
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
                  ) : visibleRecords.length === 0 ? (
                    <tr><td colSpan={6} className="empty-row">No records match the selected filters.</td></tr>
                  ) : (
                    visibleRecords.map((r) => {
                      const cat = getTimingCategory(r)
                      return (
                        <tr key={r.id}>
                          <td>{r.date}</td>
                          <td><StatusBadge status={r.status} /></td>
                          <td className={`tm-cell tm-${cat}`}>{r.check_in || '—'}</td>
                          <td className={`tm-cell tm-${cat}`}>{r.check_out || '—'}</td>
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
                      )
                    })
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