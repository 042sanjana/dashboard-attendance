import React, { useState, useRef, useCallback } from 'react'
import { X, UploadCloud, FileSpreadsheet, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'
import { uploadFile } from '../api.js'

export default function UploadModal({ onClose, onSuccess }) {
  const [file, setFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [status, setStatus] = useState('idle') // idle | uploading | success | error
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const inputRef = useRef(null)

  const pickFile = useCallback((f) => {
    if (!f) return
    const validExt = /\.(xlsx|xls)$/i.test(f.name)
    if (!validExt) {
      setErrorMsg('Only .xlsx or .xls files are supported.')
      setStatus('error')
      return
    }
    setErrorMsg('')
    setStatus('idle')
    setFile(f)
  }, [])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files?.[0]) pickFile(e.dataTransfer.files[0])
  }

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading')
    setProgress(0)
    setErrorMsg('')
    try {
      const res = await uploadFile(file, (evt) => {
        if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100))
      })
      setResult(res.data)
      setStatus('success')
      onSuccess?.()
    } catch (err) {
      setStatus('error')
      setErrorMsg(
        err?.response?.data?.detail ||
          err?.message ||
          'Something went wrong while uploading the file.'
      )
    }
  }

  const reset = () => {
    setFile(null)
    setResult(null)
    setStatus('idle')
    setErrorMsg('')
    setProgress(0)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Attendance Excel</h2>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="modal-body">
          {status !== 'success' && (
            <>
              <p className="modal-hint">
                Expected columns: <strong>Emp No, Employee Name, Date, Attendance Status,
                CheckIn, CheckOut, Comments</strong>. New employees are added automatically;
                existing attendance for the same employee and date is updated, not duplicated.
              </p>

              <div
                className={`dropzone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  hidden
                  onChange={(e) => pickFile(e.target.files?.[0])}
                />
                {file ? (
                  <>
                    <FileSpreadsheet size={32} />
                    <p className="dz-filename">{file.name}</p>
                    <p className="dz-filesize">{(file.size / 1024).toFixed(1)} KB</p>
                  </>
                ) : (
                  <>
                    <UploadCloud size={32} />
                    <p>Drag & drop your Excel file here, or click to browse</p>
                    <span className="dz-note">.xlsx or .xls, up to 15MB</span>
                  </>
                )}
              </div>

              {status === 'error' && errorMsg && (
                <div className="alert alert-error">
                  <AlertTriangle size={16} />
                  <span>{errorMsg}</span>
                </div>
              )}

              {status === 'uploading' && (
                <div className="progress-bar-track">
                  <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
                </div>
              )}

              <div className="modal-actions">
                <button className="secondary-btn" onClick={onClose}>Cancel</button>
                <button
                  className="primary-btn"
                  disabled={!file || status === 'uploading'}
                  onClick={handleUpload}
                >
                  {status === 'uploading' ? (
                    <><Loader2 size={16} className="spin" /> Uploading…</>
                  ) : (
                    <><UploadCloud size={16} /> Upload & Process</>
                  )}
                </button>
              </div>
            </>
          )}

          {status === 'success' && result && (
            <div className="upload-result">
              <div className="alert alert-success">
                <CheckCircle2 size={18} />
                <span>File processed successfully.</span>
              </div>

              <div className="result-stats">
                <div className="result-stat">
                  <span className="result-stat-value">{result.total_rows}</span>
                  <span className="result-stat-label">Total Rows</span>
                </div>
                <div className="result-stat stat-new">
                  <span className="result-stat-value">{result.new_employees}</span>
                  <span className="result-stat-label">New Employees</span>
                </div>
                <div className="result-stat stat-inserted">
                  <span className="result-stat-value">{result.inserted_attendance}</span>
                  <span className="result-stat-label">Inserted Records</span>
                </div>
                <div className="result-stat stat-updated">
                  <span className="result-stat-value">{result.updated_attendance}</span>
                  <span className="result-stat-label">Updated Records</span>
                </div>
                <div className="result-stat stat-error">
                  <span className="result-stat-value">{result.error_rows}</span>
                  <span className="result-stat-label">Errors</span>
                </div>
              </div>

              {result.error_rows > 0 && (
                <div className="preview-section">
                  <h4>Row Errors</h4>
                  <div className="preview-scroll">
                    <table className="preview-table">
                      <thead><tr><th>Row</th><th>Reason</th></tr></thead>
                      <tbody>
                        {result.errors.map((e, i) => (
                          <tr key={i}><td>{e.row}</td><td>{e.reason}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {result.preview_inserted?.length > 0 && (
                <div className="preview-section">
                  <h4>Newly Inserted (preview)</h4>
                  <div className="preview-scroll">
                    <table className="preview-table">
                      <thead><tr><th>Emp ID</th><th>Name</th><th>Date</th><th>Status</th></tr></thead>
                      <tbody>
                        {result.preview_inserted.map((r, i) => (
                          <tr key={i}><td>{r.emp_id}</td><td>{r.name}</td><td>{r.date}</td><td>{r.status}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {result.preview_updated?.length > 0 && (
                <div className="preview-section">
                  <h4>Updated Records (preview)</h4>
                  <div className="preview-scroll">
                    <table className="preview-table">
                      <thead><tr><th>Emp ID</th><th>Name</th><th>Date</th><th>Status</th></tr></thead>
                      <tbody>
                        {result.preview_updated.map((r, i) => (
                          <tr key={i}><td>{r.emp_id}</td><td>{r.name}</td><td>{r.date}</td><td>{r.status}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="modal-actions">
                <button className="secondary-btn" onClick={reset}>Upload Another File</button>
                <button className="primary-btn" onClick={onClose}>Done</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
