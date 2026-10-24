import React, { useState } from 'react'
import { Trash2 } from 'lucide-react'
import ConfirmDialog from './ConfirmDialog.jsx'
import { resetAllData } from '../api.js'

export default function ResetDataButton({
  onReset,
  className = 'nav-item',
}) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  const confirm = async () => {
    if (busy) {
      return
    }

    setBusy(true)

    try {
      await resetAllData()

      setOpen(false)

      if (onReset) {
        await onReset()
      }
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        'Failed to reset data.'

      alert(message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className={className}
        onClick={() => setOpen(true)}
        disabled={busy}
      >
        <Trash2 size={18} />

        <span>
          {busy
            ? 'Resetting...'
            : 'Reset All Data'}
        </span>
      </button>

      {open && (
        <ConfirmDialog
          title="Reset all attendance data?"
          message="This permanently deletes every employee, every attendance record, and the upload history — giving you a completely fresh, empty dashboard. This cannot be undone."
          confirmLabel="Reset Everything"
          busy={busy}
          onConfirm={confirm}
          onCancel={() => {
            if (!busy) {
              setOpen(false)
            }
          }}
        />
      )}
    </>
  )
}