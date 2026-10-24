import React from 'react'
import { UploadCloud, Bell } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Topbar({ onUploadClick }) {
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <header className="topbar">
      <div>
        <Link to="/" className="topbar-title-link">
          <h1 className="topbar-title">Employee Attendance Dashboard</h1>
        </Link>
        <p className="topbar-date">{today}</p>
      </div>
      <div className="topbar-actions">
        <button className="icon-btn" title="Notifications">
          <Bell size={18} />
        </button>
        <button className="primary-btn" onClick={onUploadClick}>
          <UploadCloud size={16} />
          Upload Excel
        </button>
        <div className="avatar">HR</div>
      </div>
    </header>
  )
}