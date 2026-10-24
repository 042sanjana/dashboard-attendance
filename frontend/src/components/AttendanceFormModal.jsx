import React, { useEffect, useState } from 'react'
import { X, Loader2, CalendarPlus, CalendarCog } from 'lucide-react'
import { createAttendance, updateAttendance } from '../api.js'

const STATUS_OPTIONS = ['Present', 'Absent', 'WFH', 'Leave', 'Half Day','Sick leave','Public Holiday','Weekly Holiday']

export default function AttendanceFormModal({ empId, record, onClose, onSuccess }) {
  const isEdit = Boolean(record)
  const [date, setDate] = useState(record?.date || new Date().toISOString().slice(0, 10))
  const [status, setStatus] = useState(record?.status || 'Present')
  const [checkIn, setCheckIn] = useState(record?.check_in || '')
  const [checkOut, setCheckOut] = useState(record?.check_out || '')
  const [comments, setComments] = useState('')
  useEffect(() => {
    setComments(record?.comments ?? '')
  }, [record])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!date || !status) {
      setError('Date and Status are required.')
      return
    }
    setSaving(true)
    setError('')
    const payload = {
      date,
      status,
      check_in: checkIn || null,
      check_out: checkOut || null,
      comments: comments
    }
    try {
      if (isEdit) {
        await updateAttendance(record.id, payload)
      } else {
        await createAttendance({ emp_id: empId, ...payload })
      }
      if (onSuccess){

        await onSuccess()
      }

      onClose()
    } catch (err) {
      console.log('422 ERROR:', err?.response?.data)


      setError(JSON.stringify(err?.response?.data?.detail || err?.response?.data ))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>
            {isEdit
              ? <><CalendarCog size={17} style={{ marginRight: 6 }} />Edit Attendance</>
              : <><CalendarPlus size={17} style={{ marginRight: 6 }} />Add Attendance</>}
          </h2>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit}>
          {!isEdit && (
            <div className="form-field">
              <label>Employee</label>
              <input type="text" className="form-input" value={empId} disabled />
            </div>
          )}

          <div className="form-row">
            <div className="form-field">
              <label>Date</label>
              <input
                type="date"
                className="form-input"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="form-field">
              <label>Status</label>
              <select className="form-input" value={status} onChange={(e) => setStatus(e.target.value)}>
                {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Check In</label>
              <input type="time" className="form-input" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
            </div>
            <div className="form-field">
              <label>Check Out</label>
              <input type="time" className="form-input" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
            </div>
          </div>

          <div className="form-field">
            <label>Comments</label>
            <input
              type="text"
              className="form-input"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Optional"
            />
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary-btn" disabled={saving}>
              {saving ? <Loader2 size={16} className="spin" /> : (isEdit ? 'Save Changes' : 'Add Record')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}