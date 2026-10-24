import React, { useState, useCallback } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import Topbar from './components/Topbar.jsx'
import Dashboard from './components/Dashboard.jsx'
import EmployeeDetail from './components/EmployeeDetail.jsx'
import UploadModal from './components/UploadModal.jsx'
import ODCTracker from './components/ODCTracker.jsx'

export default function App() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const navigate = useNavigate()

  // Bumping refreshKey forces Dashboard & children to refetch data
  const triggerRefresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  const handleReset = useCallback(() => {
    triggerRefresh()
    navigate('/') // in case the user was viewing a now-deleted employee's detail page
  }, [triggerRefresh, navigate])

  return (
    <div className="app-shell">
      <Sidebar onUploadClick={() => setUploadOpen(true)} onReset={handleReset} />
      <div className="main-area">
        <Topbar onUploadClick={() => setUploadOpen(true)} />
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard refreshKey={refreshKey} />} />
            <Route path="/employees/:empId" element={<EmployeeDetail />} />
            <Route path="/odc-tracker" element={<ODCTracker />} />
          </Routes>
        </div>
      </div>
      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onSuccess={() => {
            triggerRefresh()
          }}
        />
      )}
    </div>
  )
}