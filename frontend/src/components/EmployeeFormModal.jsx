import React, { useState } from 'react'
import { X, Loader2, UserPlus, UserCog } from 'lucide-react'
import { createEmployee, updateEmployee } from '../api.js'

export default function EmployeeFormModal({ employee, onClose, onSuccess }) {
  const isEdit = Boolean(employee)
  const [empId, setEmpId] = useState(employee?.emp_id || '')
  const [name, setName] = useState(employee?.name || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!empId.trim() || !name.trim()) {
      setError('Emp ID and Name are both required.')
      return
    }
    setSaving(true)
    setError('')
    try {
      if (isEdit) {
        await updateEmployee(empId.trim(), { name: name.trim() })
      } else {
        await createEmployee({ emp_id: empId.trim(), name: name.trim() })
      }
      onSuccess?.()
      onClose()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" style={{ maxWidth: 420 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{isEdit ? <><UserCog size={17} style={{ marginRight: 6 }} />Edit Employee</> : <><UserPlus size={17} style={{ marginRight: 6 }} />Add Employee</>}</h2>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit}>
          <div className="form-field">
            <label>Emp ID</label>
            <input
              type="text"
              value={empId}
              onChange={(e) => setEmpId(e.target.value)}
              disabled={isEdit}
              placeholder="e.g. EMP009"
              className="form-input"
              autoFocus={!isEdit}
            />
          </div>

          <div className="form-field">
            <label>Employee Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jordan Lee"
              className="form-input"
              autoFocus={isEdit}
            />
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary-btn" disabled={saving}>
              {saving ? <Loader2 size={16} className="spin" /> : (isEdit ? 'Save Changes' : 'Add Employee')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}