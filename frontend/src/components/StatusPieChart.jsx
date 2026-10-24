import React from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'

const COLOR_MAP = {
  Present: '#16a34a',
  Absent: '#dc2626',
  WFH: '#7c3aed',
  Leave: '#d97706',
  'Half Day': '#0891b2',
}

export default function StatusPieChart({ data, loading }) {
  const chartData = (data || []).filter((d) => d.value > 0)
  const total = chartData.reduce((sum, d) => sum + d.value, 0)

  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <h3>Today's Status Breakdown</h3>
        <span className="chart-subtitle">{total} record{total === 1 ? '' : 's'}</span>
      </div>
      {loading ? (
        <div className="chart-placeholder">Loading chart…</div>
      ) : chartData.length === 0 ? (
        <div className="chart-placeholder">No data for this date.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={95}
              paddingAngle={2}
            >
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={COLOR_MAP[entry.name] || '#94a3b8'} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 13 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
