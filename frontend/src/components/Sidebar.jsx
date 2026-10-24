import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, UploadCloud, BarChart3, Building2, ClipboardList } from 'lucide-react'
import ResetDataButton from './ResetDataButton.jsx'

export default function Sidebar({ onUploadClick, onReset }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon"><Building2 size={20} /></div>
        <div>
          <div className="brand-title">HR Portal</div>
          <div className="brand-subtitle">Attendance System</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </NavLink>
        <NavLink to="/odc-tracker" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><ClipboardList size={18} /><span>ODC Tracker</span></NavLink>
        <a className="nav-item" href="#employees-section">
          <Users size={18} />
          <span>Employees</span>
        </a>
        <a className="nav-item" href="#charts-section">
          <BarChart3 size={18} />
          <span>Analytics</span>
        </a>
        <button className="nav-item nav-upload" onClick={onUploadClick}>
          <UploadCloud size={18} />
          <span>Upload Excel</span>
        </button>
        <ResetDataButton onReset={onReset} className="nav-item nav-reset" />
      </nav>

      <div className="sidebar-footer">
        <div className="footer-card">
          <p>Need to add attendance?</p>
          <button onClick={onUploadClick}>Upload File</button>
        </div>
      </div>
    </aside>
  )
}