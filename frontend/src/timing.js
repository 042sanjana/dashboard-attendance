// Check-in / check-out categories. Same names as app/analytics.py:
//   complete       (green)  both present and valid
//   both_missing   (red)    no check-in and no check-out
//   either_missing (orange) exactly one of them missing
//   invalid        (purple) check-out not after check-in, or shift of 24h or more
// CSS classes: tm-<category> (see index.css).

export const TIMING_ORDER = ['complete', 'both_missing', 'either_missing', 'invalid']

export const TIMING_META = {
  complete: { label: 'Complete', hint: 'Check-in and check-out valid' },
  both_missing: { label: 'Both missing', hint: 'No check-in or check-out' },
  either_missing: { label: 'One missing', hint: 'Check-in or check-out missing' },
  invalid: { label: 'Invalid', hint: 'Out not after in, or 24h+ shift' },
}

const DAY_SECONDS = 24 * 60 * 60

function toSeconds(t) {
  if (!t) return null
  const [h = '0', m = '0', s = '0'] = String(t).split(':')
  const sec = Number(h) * 3600 + Number(m) * 60 + Number(s)
  return Number.isNaN(sec) ? null : sec
}

// record: { check_in, check_out, check_in_date?, check_out_date? }
// Overnight shifts are only resolved when BOTH dates are present.
export function getTimingCategory(record) {
  const inSec = toSeconds(record?.check_in)
  const outSec = toSeconds(record?.check_out)
  if (inSec === null && outSec === null) return 'both_missing'
  if (inSec === null || outSec === null) return 'either_missing'

  let diff = outSec - inSec
  if (record.check_in_date && record.check_out_date) {
    const d1 = Date.parse(`${record.check_in_date}T00:00:00Z`)
    const d2 = Date.parse(`${record.check_out_date}T00:00:00Z`)
    if (!Number.isNaN(d1) && !Number.isNaN(d2)) diff += Math.round((d2 - d1) / 1000)
  }
  return diff <= 0 || diff >= DAY_SECONDS ? 'invalid' : 'complete'
}