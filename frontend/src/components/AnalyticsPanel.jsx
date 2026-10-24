import React, { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Clock, Timer, Users, AlertTriangle, SlidersHorizontal } from 'lucide-react'
import {
  getAnalyticsFilters,
  getAttendanceGraph,
  getWorkingHours,
  getDailyRecords,
} from '../api.js'

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const STATUS_COLORS = {
  Present: '#16a34a',
  Absent: '#dc2626',
  WFH: '#7c3aed',
  Leave: '#d97706',
  'Half Day': '#0891b2',
  'Sick leave': '#db2777',
  'Public Holiday': '#2563eb',
  'Weekly Holiday': '#64748b',
}

const FLAG_LABELS = {
  no_timings: 'no timings',
  missing_check_in: 'missing check-in',
  missing_check_out: 'missing check-out',
  invalid_order: 'check-out not after check-in',
}

const AXIS = { fontSize: 12, fill: '#64748b' }
const TOOLTIP_STYLE = { borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 13 }

const colorOf = (status) => STATUS_COLORS[status] || '#94a3b8'

// 8.5 -> "8h 30m"; null -> "—"  (never invents a value)
function hm(hours) {
  if (hours === null || hours === undefined) return '—'
  const mins = Math.round(hours * 60)
  return `${Math.floor(mins / 60)}h ${String(mins % 60).padStart(2, '0')}m`
}

function StatusPill({ status }) {
  const c = colorOf(status)
  return (
    <span className="an-pill" style={{ background: `${c}1f`, color: c }}>
      {status}
    </span>
  )
}

function Segmented({ value, onChange, options }) {
  return (
    <div className="an-seg">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          className={`an-seg-btn ${value === o.value ? 'active' : ''}`}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function HoursTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="an-tooltip">
      <strong>{p.key}</strong>
      <div>Total: {hm(p.total_hours)}</div>
      <div>Avg / day: {hm(p.avg_hours_per_day)}</div>
      <div>{p.valid_records} counted · {p.excluded_records} excluded</div>
      {p.employees_counted > 0 && <div>{p.employees_counted} employee(s)</div>}
    </div>
  )
}

export default function AnalyticsPanel({ refreshKey }) {
  // ---- filters (shared by every graph and table below) ----
  const [filters, setFilters] = useState(null)
  const [empId, setEmpId] = useState('all')
  const [statuses, setStatuses] = useState([]) // empty = all statuses
  const [year, setYear] = useState(null)
  const [month, setMonth] = useState(null)
  const [graphView, setGraphView] = useState('monthly') // monthly | yearly
  const [hoursPeriod, setHoursPeriod] = useState('daily') // daily | monthly | yearly
  const [metric, setMetric] = useState('total') // total | average

  // ---- data ----
  const [graph, setGraph] = useState(null)
  const [hours, setHours] = useState(null)
  const [records, setRecords] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Load dropdown options. Re-runs after uploads / CRUD / reset (refreshKey).
  useEffect(() => {
    let cancelled = false
    getAnalyticsFilters()
      .then((res) => {
        if (cancelled) return
        const f = res.data
        setFilters(f)
        setEmpId((prev) =>
          prev === 'all' || f.employees.some((e) => e.emp_id === prev) ? prev : 'all'
        )
        setYear((prev) =>
          prev !== null && f.years.includes(prev)
            ? prev
            : f.latest_date ? Number(f.latest_date.slice(0, 4)) : null
        )
        setMonth((prev) =>
          prev !== null ? prev : f.latest_date ? Number(f.latest_date.slice(5, 7)) : null
        )
      })
      .catch(() => {
        if (!cancelled) setError('Could not load analytics filters. Is the backend running?')
      })
    return () => { cancelled = true }
  }, [refreshKey])

  // Re-fetch graphs + tables whenever ANY filter changes.
  useEffect(() => {
    if (!filters || year === null || month === null) {
      setLoading(false)
      return undefined
    }
    let cancelled = false
    setLoading(true)
    setError('')
    const common = {
      emp_id: empId === 'all' ? undefined : empId,
      status: statuses.length ? statuses.join(',') : undefined,
    }
    Promise.all([
      getAttendanceGraph({ ...common, view: graphView, year, month }),
      getWorkingHours({ ...common, period: hoursPeriod, year, month }),
      getDailyRecords({ ...common, year, month, limit: 500 }),
    ])
      .then(([g, h, r]) => {
        if (cancelled) return
        setGraph(g.data)
        setHours(h.data)
        setRecords(r.data)
      })
      .catch((err) => {
        if (!cancelled) setError(err?.response?.data?.detail || 'Could not load analytics data.')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [filters, empId, statuses, year, month, graphView, hoursPeriod])

  const graphData = useMemo(
    () => (graph?.points || []).map((p) => ({ label: p.label, ...p.counts })),
    [graph]
  )
  const hoursData = useMemo(
    () =>
      (hours?.points || []).map((p) => ({
        ...p,
        value: metric === 'total' ? p.total_hours : p.avg_hours_per_day,
      })),
    [hours, metric]
  )

  const toggleStatus = (s) =>
    setStatuses((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]))

  // ---------- early states ----------
  if (!filters) {
    return (
      <section className="an-section" id="analytics-section">
        <div className="chart-card">
          <div className="chart-placeholder">{error || 'Loading analytics…'}</div>
        </div>
      </section>
    )
  }
  if (filters.years.length === 0) {
    return (
      <section className="an-section" id="analytics-section">
        <div className="chart-card">
          <div className="chart-placeholder">
            No attendance data yet. Upload an Excel file to see analytics.
          </div>
        </div>
      </section>
    )
  }

  const monthName = month ? MONTHS[month - 1] : ''
  const empName =
    empId === 'all'
      ? 'All employees'
      : filters.employees.find((e) => e.emp_id === empId)?.name || empId
  const hoursScope =
    hoursPeriod === 'daily' ? `${monthName} ${year}` : hoursPeriod === 'monthly' ? `${year}` : 'All years'
  const hoursTitle =
    hoursPeriod === 'daily' ? 'Daily working hours' : hoursPeriod === 'monthly' ? 'Monthly working hours' : 'Yearly working hours'
  const totals = hours?.totals
  const breakdown = totals
    ? Object.entries(totals.excluded_breakdown || {})
        .map(([k, v]) => `${v} ${FLAG_LABELS[k] || k}`)
        .join(' · ')
    : ''
  const hasHoursData = hoursData.some((p) => p.value !== null && p.value !== undefined)

  return (
    <section className={`an-section ${loading ? 'is-loading' : ''}`} id="analytics-section">
      <div className="an-header">
        <h2>Attendance &amp; Working-Hours Analytics</h2>
        <p>
          {empName}
          {statuses.length ? ` · ${statuses.join(', ')}` : ' · all statuses'}
        </p>
      </div>

      {error && <div className="alert alert-error page-alert">{error}</div>}

      {/* ---------------- Filters ---------------- */}
      <div className="chart-card">
        <div className="an-filters-title"><SlidersHorizontal size={15} /> Filters</div>
        <div className="an-filters">
          <div className="an-field">
            <label>Employee</label>
            <select className="form-input" value={empId} onChange={(e) => setEmpId(e.target.value)}>
              <option value="all">All employees</option>
              {filters.employees.map((e) => (
                <option key={e.emp_id} value={e.emp_id}>{e.name} ({e.emp_id})</option>
              ))}
            </select>
          </div>
          <div className="an-field">
            <label>Year</label>
            <select className="form-input" value={year ?? ''} onChange={(e) => setYear(Number(e.target.value))}>
              {filters.years.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div className="an-field">
            <label>Month</label>
            <select className="form-input" value={month ?? ''} onChange={(e) => setMonth(Number(e.target.value))}>
              {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
            </select>
          </div>
          <div className="an-field">
            <label>Attendance graph</label>
            <Segmented
              value={graphView}
              onChange={setGraphView}
              options={[{ value: 'monthly', label: 'Monthly' }, { value: 'yearly', label: 'Yearly' }]}
            />
          </div>
          <div className="an-field">
            <label>Hours summary</label>
            <Segmented
              value={hoursPeriod}
              onChange={setHoursPeriod}
              options={[
                { value: 'daily', label: 'Daily' },
                { value: 'monthly', label: 'Monthly' },
                { value: 'yearly', label: 'Yearly' },
              ]}
            />
          </div>
        </div>

        <div className="an-chips">
          <span className="an-chips-label">Status</span>
          <button
            type="button"
            className={`an-chip ${statuses.length === 0 ? 'active' : ''}`}
            onClick={() => setStatuses([])}
          >
            All
          </button>
          {filters.statuses.map((s) => {
            const on = statuses.includes(s)
            return (
              <button
                key={s}
                type="button"
                className={`an-chip ${on ? 'active' : ''}`}
                style={on ? { background: colorOf(s), borderColor: colorOf(s), color: '#fff' } : undefined}
                onClick={() => toggleStatus(s)}
              >
                <i className="an-dot" style={{ background: on ? '#fff' : colorOf(s) }} />
                {s}
              </button>
            )
          })}
        </div>
      </div>

      {/* ---------------- Hours summary cards ---------------- */}
      <div className="an-stats">
        <div className="an-stat">
          <Clock size={18} />
          <div>
            <span className="an-stat-value">{hm(totals?.total_hours)}</span>
            <span className="an-stat-label">Total hours · {hoursScope}</span>
          </div>
        </div>
        <div className="an-stat">
          <Timer size={18} />
          <div>
            <span className="an-stat-value">{hm(totals?.avg_hours_per_day)}</span>
            <span className="an-stat-label">Average per working day</span>
          </div>
        </div>
        <div className="an-stat">
          <Users size={18} />
          <div>
            <span className="an-stat-value">{totals?.valid_records ?? 0}</span>
            <span className="an-stat-label">Days with valid timings</span>
          </div>
        </div>
        <div className="an-stat an-stat-warn">
          <AlertTriangle size={18} />
          <div>
            <span className="an-stat-value">{totals?.excluded_records ?? 0}</span>
            <span className="an-stat-label">
              Excluded from hours{breakdown ? ` (${breakdown})` : ''}
            </span>
          </div>
        </div>
      </div>

      {/* ---------------- Charts ---------------- */}
      <div className="an-charts">
        <div className="chart-card">
          <div className="chart-card-header">
            <h3>Attendance — {graphView === 'monthly' ? `${monthName} ${year}` : year}</h3>
            <span className="chart-subtitle">{graph ? `${graph.total_records} records` : ''}</span>
          </div>
          {!graph ? (
            <div className="chart-placeholder">Loading chart…</div>
          ) : graph.total_records === 0 ? (
            <div className="chart-placeholder">No attendance records match these filters.</div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={graphData} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" />
                <XAxis dataKey="label" tick={AXIS} axisLine={{ stroke: '#e2e8f0' }} />
                <YAxis tick={AXIS} axisLine={{ stroke: '#e2e8f0' }} allowDecimals={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(79,70,229,0.06)' }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {graph.series.map((s) => (
                  <Bar key={s} dataKey={s} stackId="a" fill={colorOf(s)} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-card">
          <div className="chart-card-header">
            <div>
              <h3>{hoursTitle}</h3>
              <span className="chart-subtitle">{hoursScope}</span>
            </div>
            <Segmented
              value={metric}
              onChange={setMetric}
              options={[{ value: 'total', label: 'Total' }, { value: 'average', label: 'Avg / day' }]}
            />
          </div>
          {!hours ? (
            <div className="chart-placeholder">Loading chart…</div>
          ) : !hasHoursData ? (
            <div className="chart-placeholder">
              No valid check-in / check-out pairs for these filters, so no hours can be calculated.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={hoursData} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" />
                <XAxis dataKey="label" tick={AXIS} axisLine={{ stroke: '#e2e8f0' }} />
                <YAxis tick={AXIS} axisLine={{ stroke: '#e2e8f0' }} tickFormatter={(v) => `${v}h`} />
                <Tooltip content={<HoursTooltip />} cursor={{ fill: 'rgba(79,70,229,0.06)' }} />
                <Bar dataKey="value" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ---------------- Team breakdown (only when "All employees") ---------------- */}
      {empId === 'all' && hours && hours.by_employee.length > 0 && (
        <div className="table-card">
          <div className="table-card-header">
            <div>
              <h3>Working hours by employee</h3>
              <span className="chart-subtitle">{hoursScope} · click a row to filter to that employee</span>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Total hours</th>
                  <th>Avg / day</th>
                  <th>Days counted</th>
                  <th>Days excluded</th>
                </tr>
              </thead>
              <tbody>
                {hours.by_employee.map((e) => (
                  <tr key={e.emp_id} className="clickable-row" onClick={() => setEmpId(e.emp_id)}>
                    <td className="emp-name-cell">
                      {e.name} <span className="mono">{e.emp_id}</span>
                    </td>
                    <td>{hm(e.total_hours)}</td>
                    <td>{hm(e.avg_hours_per_day)}</td>
                    <td>{e.valid_days}</td>
                    <td>{e.excluded_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---------------- Daily check-in / check-out table ---------------- */}
      <div className="table-card">
        <div className="table-card-header">
          <div>
            <h3>Daily check-in / check-out</h3>
            <span className="chart-subtitle">
              {monthName} {year} · {records ? records.total : 0} records
              {records?.summary?.total_hours != null ? ` · ${hm(records.summary.total_hours)} total` : ''}
            </span>
          </div>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Employee</th>
                <th>Status</th>
                <th>Check in</th>
                <th>Check out</th>
                <th>Hours worked</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {!records ? (
                <tr><td colSpan={7} className="empty-row">Loading records…</td></tr>
              ) : records.records.length === 0 ? (
                <tr><td colSpan={7} className="empty-row">No records match these filters.</td></tr>
              ) : (
                records.records.map((r) => (
                  <tr key={r.id}>
                    <td>{r.date}</td>
                    <td className="emp-name-cell">
                      {r.name} <span className="mono">{r.emp_id}</span>
                    </td>
                    <td><StatusPill status={r.status} /></td>
                    <td>{r.check_in || '—'}</td>
                    <td>{r.check_out || '—'}</td>
                    <td><strong>{r.worked_display || '—'}</strong></td>
                    <td>
                      {r.timing_note && (
                        <span className={`an-flag ${r.timing_flag === 'no_timings' ? 'muted' : 'warn'}`}>
                          {r.timing_flag !== 'no_timings' && <AlertTriangle size={13} />}
                          {r.timing_note}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {records && records.total > records.records.length && (
          <div className="an-more">
            Showing the latest {records.records.length} of {records.total} records. Narrow the
            filters to see the rest.
          </div>
        )}
      </div>
    </section>
  )
}