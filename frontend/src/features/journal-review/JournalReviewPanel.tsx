import { useMemo, useState } from 'react'

import { StatusPill } from '../../components/StatusPill'
import type {
  Account,
  InvoiceBundle,
  JournalEntry,
  JournalPosting,
  JournalPostingUpdateInput,
} from '../../lib/types/api'

interface JournalReviewPanelProps {
  accounts?: Account[]
  activeAccountIds: Set<string>
  bundle: InvoiceBundle | null
  isApproving: boolean
  isDeclining: boolean
  isGenerating: boolean
  isSavingEdits?: boolean
  onApprove: () => Promise<void>
  onDecline: (reason: string) => Promise<void>
  onGenerate: () => Promise<void>
  onSaveEdits?: (postings: JournalPostingUpdateInput[]) => Promise<void>
}

function toNumber(value: string): number | null {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function postingIsValidAmount(posting: JournalPosting): boolean {
  const debit = toNumber(posting.debit_amount)
  const credit = toNumber(posting.credit_amount)
  if (debit === null || credit === null) {
    return false
  }
  if (debit < 0 || credit < 0) {
    return false
  }
  return (debit > 0 && credit === 0) || (credit > 0 && debit === 0)
}

function collectApprovalViolations(entry: JournalEntry, activeAccountIds: Set<string>): string[] {
  const errors: string[] = []

  const totalDebit = toNumber(entry.total_debit)
  const totalCredit = toNumber(entry.total_credit)
  if (totalDebit === null || totalCredit === null) {
    errors.push('Totals are not numeric.')
  } else if (Math.abs(totalDebit - totalCredit) > 0.00001) {
    errors.push('Total debit and total credit are not balanced.')
  }

  for (const posting of entry.postings) {
    if (!postingIsValidAmount(posting)) {
      errors.push(`Line ${posting.line_no}: amount values are invalid.`)
    }
    if (!activeAccountIds.has(posting.account_id)) {
      errors.push(`Line ${posting.line_no}: account is missing or inactive.`)
    }
  }

  return errors
}

function formatMoney(value: string, currency: string): string {
  const parsed = toNumber(value)
  if (parsed === null) {
    return value
  }
  return `${parsed.toFixed(2)} ${currency}`
}

export function JournalReviewPanel({
  activeAccountIds,
  bundle,
  isApproving,
  isDeclining,
  isGenerating,
  onApprove,
  onDecline,
  onGenerate,
}: JournalReviewPanelProps) {
  const [declineReason, setDeclineReason] = useState('')

  const entry = bundle?.journal_entry ?? null
  const approvalViolations = useMemo(() => {
    if (entry === null || entry.status !== 'pending') {
      return []
    }
    return collectApprovalViolations(entry, activeAccountIds)
  }, [activeAccountIds, entry])

  if (bundle === null) {
    return (
      <section className="card review-panel">
        <h2>Journal Entry Review</h2>
      </section>
    )
  }

  if (entry === null) {
    return (
      <section className="card review-panel">
        <h2>Journal Entry Review</h2>
        <div className="decision-panel">
          <button disabled={isGenerating} onClick={() => void onGenerate()} type="button">
            {isGenerating ? 'Generating...' : 'Generate suggestion'}
          </button>
        </div>
      </section>
    )
  }

  const canApprove = entry.status === 'pending' && approvalViolations.length === 0
  const canDecline = entry.status === 'pending'

  return (
    <section className="card review-panel">
      <div className="review-header">
        <h2>Journal Entry Review</h2>
        <StatusPill status={entry.status} />
      </div>

      {approvalViolations.length > 0 ? (
        <div className="warning-panel" role="alert">
          <strong>Approval blocked</strong>
          <ul>
            {approvalViolations.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Line</th>
              <th>Account</th>
              <th>Description</th>
              <th>Debit</th>
              <th>Credit</th>
            </tr>
          </thead>
          <tbody>
            {entry.postings.map((posting) => (
              <tr key={posting.id}>
                <td>{posting.line_no}</td>
                <td>{`${posting.account_code_snapshot} ${posting.account_name_snapshot}`}</td>
                <td>{posting.description ?? '-'}</td>
                <td>{formatMoney(posting.debit_amount, entry.currency)}</td>
                <td>{formatMoney(posting.credit_amount, entry.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="decision-panel">
        <button disabled={!canApprove || isApproving} onClick={() => void onApprove()} type="button">
          {isApproving ? 'Approving...' : 'Approve'}
        </button>
        <div className="decline-group">
          <input
            placeholder="Decline reason (optional)"
            value={declineReason}
            onChange={(event) => setDeclineReason(event.target.value)}
          />
          <button
            className="button-secondary"
            disabled={!canDecline || isDeclining}
            onClick={() => void onDecline(declineReason)}
            type="button"
          >
            {isDeclining ? 'Declining...' : 'Decline'}
          </button>
        </div>
      </div>
    </section>
  )
}
