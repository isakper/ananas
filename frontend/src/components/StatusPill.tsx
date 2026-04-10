import type { JournalStatus } from '../lib/types/api'

interface StatusPillProps {
  status: JournalStatus
}

const LABEL_BY_STATUS: Record<JournalStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  declined: 'Declined',
}

export function StatusPill({ status }: StatusPillProps) {
  return <span className={`status-pill status-pill--${status}`}>{LABEL_BY_STATUS[status]}</span>
}
