import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

const COLORS = {
  present: '#16a34a',
  absent: '#dc2626',
  wfh: '#7c3aed',
  leave: '#d97706',
  half_day: '#0891b2',
}

const LABELS = {
  present: 'Present',
  absent: 'Absent',
  wfh: 'WFH',
  leave: 'Leave',
  half_day: 'Half Day',
}

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function AttendanceTrendChart({ data, loading }) {
  const chartData = (data || []).map((d) => ({ ...d, label: formatDate(d.date) }))

  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <h3>Attendance Trend</h3>
        <span className="chart-subtitle">Last {chartData.length} days</span>
      </div>
      {loading ? (
        <div className="chart-placeholder">Loading chart…</div>
      ) : chartData.length === 0 ? (
        <div className="chart-placeholder">No attendance data yet. Upload an Excel file to get started.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={{ stroke: '#e2e8f0' }} />
            <YAxis tick={{ fontSize: 12, fill: '#64748b' }} axisLine={{ stroke: '#e2e8f0' }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 13 }}
              labelStyle={{ fontWeight: 600 }}
            />
            <Legend
              formatter={(value) => LABELS[value] || value}
              wrapperStyle={{ fontSize: 12 }}
            />
            {Object.keys(COLORS).map((key) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={COLORS[key]}
                strokeWidth={2.5}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
