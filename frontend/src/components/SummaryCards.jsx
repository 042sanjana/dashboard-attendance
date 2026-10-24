import React from 'react'
import { Users, CheckCircle2, Home, XCircle, CalendarClock } from 'lucide-react'

const CARDS = [
  { key: 'total_employees', label: 'Total Employees', icon: Users, accent: 'blue' },
  { key: 'present', label: 'Present', icon: CheckCircle2, accent: 'green' },
  { key: 'wfh', label: 'Work From Home', icon: Home, accent: 'purple' },
  { key: 'absent', label: 'Absent', icon: XCircle, accent: 'red' },
  { key: 'leave', label: 'On Leave', icon: CalendarClock, accent: 'amber' },
]

export default function SummaryCards({ summary, loading }) {
  return (
    <div className="summary-grid">
      {CARDS.map(({ key, label, icon: Icon, accent }) => (
        <div className={`summary-card accent-${accent}`} key={key}>
          <div className="summary-card-icon">
            <Icon size={22} />
          </div>
          <div className="summary-card-body">
            <span className="summary-card-value">
              {loading ? '—' : (summary?.[key] ?? 0)}
            </span>
            <span className="summary-card-label">{label}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
