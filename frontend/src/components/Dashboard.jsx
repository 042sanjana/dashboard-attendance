import React, { useEffect, useState, useCallback } from 'react'
import SummaryCards from './SummaryCards.jsx'
import AttendanceTrendChart from './AttendanceTrendChart.jsx'
import StatusPieChart from './StatusPieChart.jsx'
import EmployeeTable from './EmployeeTable.jsx'
import { getSummary, getChartData, getStatusDistribution, getEmployees } from '../api.js'
import AnalyticsPanel from './AnalyticsPanel.jsx'      // <-- add
function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export default function Dashboard({ refreshKey }) {
  const [selectedDate, setSelectedDate] = useState(todayIso())
  const [summary, setSummary] = useState(null)
  const [trend, setTrend] = useState([])
  const [distribution, setDistribution] = useState([])
  const [employees, setEmployees] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [employeesLoading, setEmployeesLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [analyticsTick, setAnalyticsTick] = useState(0)  // <-- add

  const loadDashboardData = useCallback(async () => {
    setLoading(true)
    setLoadError('')
    try {
      const [summaryRes, trendRes, distRes] = await Promise.all([
        getSummary(selectedDate),
        getChartData(14),
        getStatusDistribution(selectedDate),
      ])
      setSummary(summaryRes.data)
      setTrend(trendRes.data)
      setDistribution(distRes.data)
    } catch (err) {
      setLoadError('Could not reach the backend API. Make sure the FastAPI server is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }, [selectedDate])

  const loadEmployees = useCallback(async () => {
    setEmployeesLoading(true)
    try {
      const res = await getEmployees({
        search: search || undefined,
        date: selectedDate || undefined,
      })
      setEmployees(res.data)
    } catch (err) {
      // silently ignore; error banner already shown for main dashboard data
    } finally {
      setEmployeesLoading(false)
    }
  }, [search, selectedDate])

  useEffect(() => {
    loadDashboardData()
  }, [loadDashboardData, refreshKey])

  useEffect(() => {
    loadEmployees()
  }, [loadEmployees, refreshKey])

  
  return (
    <div className="dashboard">
      {loadError && (
        <div className="alert alert-error page-alert">{loadError}</div>
      )}

      <SummaryCards summary={summary} loading={loading} />

      <div className="charts-grid" id="charts-section">
        <AttendanceTrendChart data={trend} loading={loading} />
        <StatusPieChart data={distribution} loading={loading} />
      </div>
      <AnalyticsPanel refreshKey={refreshKey } />  
      
      <EmployeeTable
        employees={employees}
        loading={employeesLoading}
        search={search}
        onSearchChange={setSearch}
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
        onDataChanged={() => { loadDashboardData(); loadEmployees(); setAnalyticsTick((t) => t + 1) }}
     
      />
      {/* <-- add */}

   
    </div>
  )
}