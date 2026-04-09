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
  accounts: Account[]
  activeAccountIds: Set<string>
  bundle: InvoiceBundle | null
  duplicateOfInvoiceId: string | null
  isApproving: boolean
  isDeclining: boolean
  isGenerating: boolean
  isSavingEdits: boolean
  onApprove: () => Promise<void>
  onDecline: (reason: string) => Promise<void>
  onGenerate: () => Promise<void>
  onSaveEdits: (postings: JournalPostingUpdateInput[]) => Promise<void>
}

interface EditablePosting {
  id: string
  line_no: number
  account_id: string
  account_label_fallback: string
  description: string
  debit_amount: string
  credit_amount: string
}

interface DraftTotals {
  debit: number | null
  credit: number | null
}

function toNumber(value: string | number): number | null {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function postingIsValidAmountValues(
  debitValue: string | number,
  creditValue: string | number,
): boolean {
  const debit = toNumber(debitValue)
  const credit = toNumber(creditValue)
  if (debit === null || credit === null) {
    return false
  }
  if (debit < 0 || credit < 0) {
    return false
  }
  return (debit > 0 && credit === 0) || (credit > 0 && debit === 0)
}

function postingIsValidAmount(posting: JournalPosting): boolean {
  return postingIsValidAmountValues(posting.debit_amount, posting.credit_amount)
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

function toEditablePosting(posting: JournalPosting): EditablePosting {
  return {
    id: posting.id,
    line_no: posting.line_no,
    account_id: posting.account_id,
    account_label_fallback: `${posting.account_code_snapshot} ${posting.account_name_snapshot}`,
    description: posting.description ?? '',
    debit_amount: String(posting.debit_amount),
    credit_amount: String(posting.credit_amount),
  }
}

function normalizeDescription(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

function normalizeAmountForComparison(value: string | number): string {
  const parsed = toNumber(value)
  if (parsed === null) {
    return String(value).trim()
  }
  return parsed.toFixed(2)
}

function normalizeEditableForComparison(postings: EditablePosting[]): string {
  return JSON.stringify(
    postings.map((posting) => ({
      account_id: posting.account_id,
      description: normalizeDescription(posting.description),
      debit_amount: normalizeAmountForComparison(posting.debit_amount),
      credit_amount: normalizeAmountForComparison(posting.credit_amount),
    })),
  )
}

function normalizeStoredForComparison(postings: JournalPosting[]): string {
  return JSON.stringify(
    postings.map((posting) => ({
      account_id: posting.account_id,
      description: posting.description,
      debit_amount: normalizeAmountForComparison(posting.debit_amount),
      credit_amount: normalizeAmountForComparison(posting.credit_amount),
    })),
  )
}

function calculateDraftTotals(postings: EditablePosting[]): DraftTotals {
  let debit = 0
  let credit = 0
  for (const posting of postings) {
    const parsedDebit = toNumber(posting.debit_amount)
    const parsedCredit = toNumber(posting.credit_amount)
    if (parsedDebit === null || parsedCredit === null) {
      return { debit: null, credit: null }
    }
    debit += parsedDebit
    credit += parsedCredit
  }
  return { debit, credit }
}

function collectEditViolations(
  postings: EditablePosting[],
  activeAccountIds: Set<string>,
  totals: DraftTotals,
): string[] {
  const errors: string[] = []
  if (postings.length === 0) {
    errors.push('At least one posting line is required.')
    return errors
  }

  for (const posting of postings) {
    if (!activeAccountIds.has(posting.account_id)) {
      errors.push(`Line ${posting.line_no}: account is missing or inactive.`)
    }
    if (!postingIsValidAmountValues(posting.debit_amount, posting.credit_amount)) {
      errors.push(
        `Line ${posting.line_no}: use a positive debit or credit amount (not both).`,
      )
    }
  }

  if (totals.debit === null || totals.credit === null) {
    errors.push('Totals are not numeric.')
  } else if (Math.abs(totals.debit - totals.credit) > 0.00001) {
    errors.push('Total debit and total credit must be balanced.')
  }

  return errors
}

function toUpdatePayload(postings: EditablePosting[]): JournalPostingUpdateInput[] {
  return postings.map((posting) => ({
    account_id: posting.account_id,
    description: normalizeDescription(posting.description),
    debit_amount: posting.debit_amount,
    credit_amount: posting.credit_amount,
  }))
}

function formatMoney(value: string | number, currency: string): string {
  const parsed = toNumber(value)
  if (parsed === null) {
    return String(value)
  }
  return `${parsed.toFixed(2)} ${currency}`
}

export function JournalReviewPanel({
  accounts,
  activeAccountIds,
  bundle,
  duplicateOfInvoiceId,
  isApproving,
  isDeclining,
  isGenerating,
  isSavingEdits,
  onApprove,
  onDecline,
  onGenerate,
  onSaveEdits,
}: JournalReviewPanelProps) {
  const [declineReason, setDeclineReason] = useState('')

  const entry = bundle?.journal_entry ?? null

  const [editablePostings, setEditablePostings] = useState<EditablePosting[]>(() => {
    if (entry === null || entry.status !== 'pending') {
      return []
    }
    return entry.postings.map(toEditablePosting)
  })

  const activeAccounts = useMemo(() => {
    return accounts.filter((account) => account.is_active)
  }, [accounts])

  const draftTotals = useMemo(() => {
    return calculateDraftTotals(editablePostings)
  }, [editablePostings])

  const approvalViolations = useMemo(() => {
    if (entry === null || entry.status !== 'pending') {
      return []
    }
    return collectApprovalViolations(entry, activeAccountIds)
  }, [activeAccountIds, entry])

  const editViolations = useMemo(() => {
    if (entry === null || entry.status !== 'pending') {
      return []
    }
    return collectEditViolations(editablePostings, activeAccountIds, draftTotals)
  }, [activeAccountIds, draftTotals, editablePostings, entry])

  const hasUnsavedChanges = useMemo(() => {
    if (entry === null || entry.status !== 'pending') {
      return false
    }
    return (
      normalizeEditableForComparison(editablePostings) !==
      normalizeStoredForComparison(entry.postings)
    )
  }, [editablePostings, entry])

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

  const canApprove =
    entry.status === 'pending' &&
    duplicateOfInvoiceId === null &&
    approvalViolations.length === 0 &&
    !hasUnsavedChanges &&
    !isSavingEdits
  const canDecline = entry.status === 'pending' && !isSavingEdits

  return (
    <section className="card review-panel">
      <div className="review-header">
        <h2>Journal Entry Review</h2>
        <StatusPill status={entry.status} />
      </div>

      {entry.status === 'pending' && hasUnsavedChanges ? (
        <div className="warning-panel" role="status">
          Save line edits before approving.
        </div>
      ) : null}

      {entry.status === 'pending' && editViolations.length > 0 ? (
        <div className="warning-panel" role="alert">
          <strong>Cannot save edits</strong>
          <ul>
            {editViolations.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : null}

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

      {duplicateOfInvoiceId !== null ? (
        <div className="warning-panel" role="alert">
          <strong>Approval blocked</strong>
          <p className="small-muted">
            Possible duplicate of invoice {duplicateOfInvoiceId.slice(0, 8)}.
          </p>
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
            {entry.status === 'pending'
              ? editablePostings.map((posting, index) => {
                  const hasActiveSelection = activeAccountIds.has(posting.account_id)
                  return (
                    <tr key={posting.id}>
                      <td>{posting.line_no}</td>
                      <td>
                        <select
                          className="table-input"
                          value={posting.account_id}
                          onChange={(event) => {
                            const accountId = event.target.value
                            setEditablePostings((current) =>
                              current.map((line, lineIndex) =>
                                lineIndex === index ? { ...line, account_id: accountId } : line,
                              ),
                            )
                          }}
                        >
                          {activeAccounts.map((account) => (
                            <option key={account.id} value={account.id}>
                              {`${account.code} ${account.name}`}
                            </option>
                          ))}
                          {!hasActiveSelection ? (
                            <option value={posting.account_id}>
                              {`${posting.account_label_fallback} (inactive)`}
                            </option>
                          ) : null}
                        </select>
                      </td>
                      <td>
                        <input
                          className="table-input"
                          type="text"
                          value={posting.description}
                          onChange={(event) => {
                            const description = event.target.value
                            setEditablePostings((current) =>
                              current.map((line, lineIndex) =>
                                lineIndex === index ? { ...line, description } : line,
                              ),
                            )
                          }}
                        />
                      </td>
                      <td>
                        <input
                          className="table-input"
                          inputMode="decimal"
                          min="0"
                          step="0.01"
                          type="number"
                          value={posting.debit_amount}
                          onChange={(event) => {
                            const debitAmount = event.target.value
                            setEditablePostings((current) =>
                              current.map((line, lineIndex) =>
                                lineIndex === index
                                  ? { ...line, debit_amount: debitAmount }
                                  : line,
                              ),
                            )
                          }}
                        />
                      </td>
                      <td>
                        <input
                          className="table-input"
                          inputMode="decimal"
                          min="0"
                          step="0.01"
                          type="number"
                          value={posting.credit_amount}
                          onChange={(event) => {
                            const creditAmount = event.target.value
                            setEditablePostings((current) =>
                              current.map((line, lineIndex) =>
                                lineIndex === index
                                  ? { ...line, credit_amount: creditAmount }
                                  : line,
                              ),
                            )
                          }}
                        />
                      </td>
                    </tr>
                  )
                })
              : entry.postings.map((posting) => (
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

      <p className="small-muted">
        Totals:{' '}
        {entry.status === 'pending' && draftTotals.debit !== null && draftTotals.credit !== null
          ? `${draftTotals.debit.toFixed(2)} / ${draftTotals.credit.toFixed(2)} ${entry.currency}`
          : `${formatMoney(entry.total_debit, entry.currency)} / ${formatMoney(entry.total_credit, entry.currency)}`}
      </p>

      <div className="decision-panel">
        {entry.status === 'pending' ? (
          <>
            <button
              className="button-secondary"
              disabled={isSavingEdits || editViolations.length > 0 || !hasUnsavedChanges}
              onClick={() => void onSaveEdits(toUpdatePayload(editablePostings))}
              type="button"
            >
              {isSavingEdits ? 'Saving...' : 'Save line edits'}
            </button>
            <button
              className="button-secondary"
              disabled={isSavingEdits || !hasUnsavedChanges}
              onClick={() => setEditablePostings(entry.postings.map(toEditablePosting))}
              type="button"
            >
              Reset edits
            </button>
          </>
        ) : null}
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
