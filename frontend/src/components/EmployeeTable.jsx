import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronRight, UserPlus, Pencil, Trash2 } from 'lucide-react'
import StatusBadge from './StatusBadge.jsx'
import EmployeeFormModal from './EmployeeFormModal.jsx'
import ConfirmDialog from './ConfirmDialog.jsx'
import { deleteEmployee } from '../api.js'

export default function EmployeeTable({
  employees,
  loading,
  search,
  onSearchChange,
  selectedDate,
  onDateChange,
  onDataChanged, // callback to refetch dashboard/employee data after a CRUD action
}) {
  const navigate = useNavigate()
  const [formOpen, setFormOpen] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const openCreate = () => { setEditingEmployee(null); setFormOpen(true) }
  const openEdit = (emp, e) => { e.stopPropagation(); setEditingEmployee(emp); setFormOpen(true) }
  const askDelete = (emp, e) => { e.stopPropagation(); setDeleteTarget(emp) }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteEmployee(deleteTarget.emp_id)
      setDeleteTarget(null)
      onDataChanged?.()
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to delete employee.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="table-card" id="employees-section">
      <div className="table-card-header">
        <div>
          <h3>Employees</h3>
          <span className="chart-subtitle">{employees.length} shown</span>
        </div>
        <div className="table-controls">
          <div className="search-box">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search by name or Emp ID…"
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
            />
          </div>
          <input
            type="date"
            className="date-input"
            value={selectedDate}
            onChange={(e) => onDateChange(e.target.value)}
          />
          <button className="primary-btn" onClick={openCreate}>
            <UserPlus size={16} /> Add Employee
          </button>
        </div>
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Emp ID</th>
              <th>Name</th>
              <th>Status ({selectedDate || 'latest'})</th>
              <th>Present</th>
              <th>Absent</th>
              <th>WFH</th>
              <th>Total Records</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="empty-row">Loading employees…</td>
              </tr>
            ) : employees.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-row">
                  No employees found. Try adjusting your search, or click "Add Employee" / upload an Excel file.
                </td>
              </tr>
            ) : (
              employees.map((emp) => (
                <tr
                  key={emp.emp_id}
                  className="clickable-row"
                  onClick={() => navigate(`/employees/${encodeURIComponent(emp.emp_id)}`)}
                >
                  <td className="mono">{emp.emp_id}</td>
                  <td className="emp-name-cell">{emp.name}</td>
                  <td><StatusBadge status={emp.latest_status} /></td>
                  <td>{emp.present_count}</td>
                  <td>{emp.absent_count}</td>
                  <td>{emp.wfh_count}</td>
                  <td>{emp.total_records}</td>
                  <td className="row-actions">
                    <button className="icon-btn sm" title="Edit" onClick={(e) => openEdit(emp, e)}>
                      <Pencil size={14} />
                    </button>
                    <button className="icon-btn sm danger" title="Delete" onClick={(e) => askDelete(emp, e)}>
                      <Trash2 size={14} />
                    </button>
                    <ChevronRight size={16} className="row-arrow" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {formOpen && (
        <EmployeeFormModal
          employee={editingEmployee}
          onClose={() => setFormOpen(false)}
          onSuccess={() => onDataChanged?.()}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Delete this employee?"
          message={`This permanently deletes ${deleteTarget.name} (${deleteTarget.emp_id}) and their entire attendance history. This cannot be undone.`}
          confirmLabel="Delete Employee"
          busy={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}