import React from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'

export default function ConfirmDialog({ title, message, confirmLabel = 'Delete', danger = true, busy, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-panel" style={{ maxWidth: 400 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-body" style={{ paddingTop: 24 }}>
          <div className="confirm-icon"><AlertTriangle size={22} /></div>
          <h3 className="confirm-title">{title}</h3>
          <p className="confirm-message">{message}</p>
          <div className="modal-actions">
            <button className="secondary-btn" onClick={onCancel} disabled={busy}>Cancel</button>
            <button
              className={danger ? 'danger-btn' : 'primary-btn'}
              onClick={onConfirm}
              disabled={busy}
            >
              {busy ? <Loader2 size={16} className="spin" /> : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}