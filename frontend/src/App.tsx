import { useCallback, useEffect, useMemo, useState } from 'react'

import './App.css'
import { StatusPill } from './components/StatusPill'
import { AccountsPanel } from './features/accounts/AccountsPanel'
import { InvoiceUploadPanel } from './features/invoice-upload/InvoiceUploadPanel'
import { JournalReviewPanel } from './features/journal-review/JournalReviewPanel'
import {
  ApiError,
  approveJournalEntry,
  createAccount as createAccountRequest,
  declineJournalEntry,
  generateJournalEntry,
  listAccounts,
  removeAccount as removeAccountRequest,
  updateJournalEntry as updateJournalEntryRequest,
  updateAccount as updateAccountRequest,
  uploadInvoice,
} from './lib/api/client'
import type { Account, InvoiceBundle, JournalPostingUpdateInput } from './lib/types/api'

type Screen = 'home' | 'invoice-management' | 'invoice-review' | 'company-setup'
type InvoiceStatus = 'pending' | 'approved' | 'declined'

interface ManagedInvoiceRecord {
  bundle: InvoiceBundle
  duplicateOfInvoiceId: string | null
  hash: string | null
  updatedAt: string
}

const ACCOUNT_FALLBACK_STATUS_CODES = new Set([404, 405, 500, 501, 502, 503])
const INVOICE_MANAGEMENT_STORAGE_KEY = 'invoice-journal-managed-invoices-v1'

function sortAccounts(accounts: Account[]): Account[] {
  return [...accounts].sort((left, right) => left.code - right.code)
}

function sortManagedInvoices(items: ManagedInvoiceRecord[]): ManagedInvoiceRecord[] {
  return [...items].sort((left, right) => {
    const leftTime = new Date(left.updatedAt).valueOf()
    const rightTime = new Date(right.updatedAt).valueOf()
    return rightTime - leftTime
  })
}

function getInvoiceStatus(bundle: InvoiceBundle): InvoiceStatus {
  return bundle.journal_entry?.status ?? 'pending'
}

function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Unexpected error. Check backend logs for details.'
}

function shouldUseLocalAccountFallback(error: unknown): boolean {
  if (error instanceof ApiError) {
    return ACCOUNT_FALLBACK_STATUS_CODES.has(error.statusCode)
  }
  return error instanceof TypeError
}

function nowIso(): string {
  return new Date().toISOString()
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.valueOf())) {
    return value
  }
  return parsed.toLocaleString()
}

function shortId(value: string): string {
  if (value.length <= 8) {
    return value
  }
  return value.slice(0, 8)
}

function loadManagedInvoices(): ManagedInvoiceRecord[] {
  if (typeof window === 'undefined') {
    return []
  }
  try {
    const raw = window.localStorage.getItem(INVOICE_MANAGEMENT_STORAGE_KEY)
    if (raw === null) {
      return []
    }
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }
    return sortManagedInvoices(parsed as ManagedInvoiceRecord[])
  } catch {
    return []
  }
}

function saveManagedInvoices(items: ManagedInvoiceRecord[]): void {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(INVOICE_MANAGEMENT_STORAGE_KEY, JSON.stringify(items))
}

function buildDemoAccounts(): Account[] {
  return sortAccounts([
    {
      id: 'demo-1',
      code: 1930,
      name: 'Företagskonto',
      is_active: true,
      created_at: '2026-04-09T09:00:00.000Z',
      updated_at: '2026-04-09T09:00:00.000Z',
    },
    {
      id: 'demo-2',
      code: 2440,
      name: 'Leverantörsskulder',
      is_active: true,
      created_at: '2026-04-09T09:00:00.000Z',
      updated_at: '2026-04-09T09:00:00.000Z',
    },
    {
      id: 'demo-3',
      code: 6530,
      name: 'IT-tjänster',
      is_active: true,
      created_at: '2026-04-09T09:00:00.000Z',
      updated_at: '2026-04-09T09:00:00.000Z',
    },
  ])
}

async function computeFileHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  if (typeof crypto !== 'undefined' && typeof crypto.subtle !== 'undefined') {
    const digest = await crypto.subtle.digest('SHA-256', buffer)
    const bytes = Array.from(new Uint8Array(digest))
    return bytes.map((byte) => byte.toString(16).padStart(2, '0')).join('')
  }
  return `${file.name}-${file.size}-${file.lastModified}`
}

function App() {
  const [screen, setScreen] = useState<Screen>('home')
  const [managedInvoices, setManagedInvoices] = useState<ManagedInvoiceRecord[]>(() =>
    loadManagedInvoices(),
  )
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [previewUrlsByInvoiceId, setPreviewUrlsByInvoiceId] = useState<Record<string, string>>({})
  const [isLocalAccountsFallback, setIsLocalAccountsFallback] = useState(false)

  const [isUploading, setIsUploading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSavingJournalEdits, setIsSavingJournalEdits] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [isDeclining, setIsDeclining] = useState(false)
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false)
  const [isMutatingAccounts, setIsMutatingAccounts] = useState(false)

  const activeAccountIds = useMemo(() => {
    return new Set(accounts.filter((account) => account.is_active).map((account) => account.id))
  }, [accounts])

  const activeAccounts = useMemo(() => {
    return accounts.filter((account) => account.is_active)
  }, [accounts])

  const selectedManagedInvoice = useMemo(() => {
    if (selectedInvoiceId === null) {
      return null
    }
    return (
      managedInvoices.find((item) => item.bundle.invoice.id === selectedInvoiceId) ?? null
    )
  }, [managedInvoices, selectedInvoiceId])

  const selectedBundle = selectedManagedInvoice?.bundle ?? null
  const selectedPreviewUrl =
    selectedInvoiceId === null ? null : (previewUrlsByInvoiceId[selectedInvoiceId] ?? null)

  const pendingInvoices = useMemo(() => {
    return managedInvoices.filter((item) => getInvoiceStatus(item.bundle) === 'pending')
  }, [managedInvoices])

  const processedInvoices = useMemo(() => {
    return managedInvoices.filter((item) => getInvoiceStatus(item.bundle) !== 'pending')
  }, [managedInvoices])

  const refreshAccounts = useCallback(async () => {
    setIsLoadingAccounts(true)
    try {
      const result = await listAccounts()
      setAccounts(sortAccounts(result))
      setIsLocalAccountsFallback(false)
    } catch (error) {
      if (shouldUseLocalAccountFallback(error)) {
        setAccounts((current) => (current.length === 0 ? buildDemoAccounts() : current))
        setIsLocalAccountsFallback(true)
      } else {
        setErrorMessage(toErrorMessage(error))
      }
    } finally {
      setIsLoadingAccounts(false)
    }
  }, [])

  useEffect(() => {
    void refreshAccounts()
  }, [refreshAccounts])

  useEffect(() => {
    if (selectedInvoiceId === null) {
      return
    }
    const stillExists = managedInvoices.some(
      (item) => item.bundle.invoice.id === selectedInvoiceId,
    )
    if (!stillExists) {
      setSelectedInvoiceId(null)
    }
  }, [managedInvoices, selectedInvoiceId])

  useEffect(() => {
    saveManagedInvoices(managedInvoices)
  }, [managedInvoices])

  useEffect(() => {
    return () => {
      for (const url of Object.values(previewUrlsByInvoiceId)) {
        URL.revokeObjectURL(url)
      }
    }
  }, [previewUrlsByInvoiceId])

  async function handleUploadFiles(files: File[]) {
    setErrorMessage(null)
    setIsUploading(true)

    try {
      const uploadedRecords: ManagedInvoiceRecord[] = []
      const previewByInvoiceId: Record<string, string> = {}
      const failures: string[] = []
      const existingByHash = new Map<string, string>(
        managedInvoices
          .filter((item): item is ManagedInvoiceRecord & { hash: string } => item.hash !== null)
          .map((item) => [item.hash, item.bundle.invoice.id]),
      )

      for (const file of files) {
        try {
          const fileHash = await computeFileHash(file)
          const duplicateOfInvoiceId = existingByHash.get(fileHash) ?? null
          const result = await uploadInvoice(file)
          const updatedAt = nowIso()
          const record: ManagedInvoiceRecord = {
            bundle: result,
            duplicateOfInvoiceId,
            hash: fileHash,
            updatedAt,
          }
          uploadedRecords.push(record)
          existingByHash.set(fileHash, result.invoice.id)
          previewByInvoiceId[result.invoice.id] = URL.createObjectURL(file)
        } catch (error) {
          failures.push(`${file.name}: ${toErrorMessage(error)}`)
        }
      }

      if (uploadedRecords.length > 0) {
        setManagedInvoices((current) => {
          const uploadedIds = new Set(uploadedRecords.map((item) => item.bundle.invoice.id))
          const withoutDuplicates = current.filter(
            (item) => !uploadedIds.has(item.bundle.invoice.id),
          )
          return sortManagedInvoices([...uploadedRecords, ...withoutDuplicates])
        })
        setSelectedInvoiceId(null)

        setPreviewUrlsByInvoiceId((current) => {
          const next = { ...current }
          for (const [invoiceId, url] of Object.entries(previewByInvoiceId)) {
            const previous = current[invoiceId]
            if (previous !== undefined) {
              URL.revokeObjectURL(previous)
            }
            next[invoiceId] = url
          }
          return next
        })
      }

      if (failures.length > 0) {
        const header =
          uploadedRecords.length === 0
            ? 'Upload failed.'
            : `Uploaded ${uploadedRecords.length} of ${files.length} files.`
        setErrorMessage(`${header} ${failures.join(' | ')}`)
      }
    } finally {
      setIsUploading(false)
    }
  }

  function updateManagedBundle(updatedBundle: InvoiceBundle) {
    setManagedInvoices((current) =>
      sortManagedInvoices(
        current.map((item) =>
          item.bundle.invoice.id === updatedBundle.invoice.id
            ? { ...item, bundle: updatedBundle, updatedAt: nowIso() }
            : item,
        ),
      ),
    )
  }

  async function handleGenerate() {
    if (selectedBundle === null) {
      return
    }

    setErrorMessage(null)
    setIsGenerating(true)

    try {
      const result = await generateJournalEntry(selectedBundle.invoice.id)
      updateManagedBundle(result)
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleSaveJournalEdits(postings: JournalPostingUpdateInput[]) {
    const entryId = selectedBundle?.journal_entry?.id
    if (entryId === undefined || selectedBundle === null) {
      return
    }

    setErrorMessage(null)
    setIsSavingJournalEdits(true)

    try {
      const updatedEntry = await updateJournalEntryRequest(entryId, postings)
      updateManagedBundle({
        ...selectedBundle,
        journal_entry: updatedEntry,
      })
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setIsSavingJournalEdits(false)
    }
  }

  async function handleApprove() {
    const entryId = selectedBundle?.journal_entry?.id
    if (entryId === undefined || selectedBundle === null) {
      return
    }

    setErrorMessage(null)
    setIsApproving(true)

    try {
      const updatedEntry = await approveJournalEntry(entryId)
      updateManagedBundle({
        ...selectedBundle,
        journal_entry: updatedEntry,
      })
      setScreen('invoice-management')
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setIsApproving(false)
    }
  }

  async function handleDecline(reason: string) {
    const entryId = selectedBundle?.journal_entry?.id
    if (entryId === undefined || selectedBundle === null) {
      return
    }

    setErrorMessage(null)
    setIsDeclining(true)

    try {
      const updatedEntry = await declineJournalEntry(entryId, reason)
      updateManagedBundle({
        ...selectedBundle,
        journal_entry: updatedEntry,
      })
      setScreen('invoice-management')
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setIsDeclining(false)
    }
  }

  async function handleCreateAccount(input: { code: number; name: string }) {
    setErrorMessage(null)
    setIsMutatingAccounts(true)
    const applyLocalCreate = () => {
      const timestamp = nowIso()
      const localAccount: Account = {
        id: `local-${crypto.randomUUID()}`,
        code: input.code,
        name: input.name,
        is_active: true,
        created_at: timestamp,
        updated_at: timestamp,
      }
      setAccounts((current) => sortAccounts([...current, localAccount]))
      setIsLocalAccountsFallback(true)
    }

    if (isLocalAccountsFallback) {
      applyLocalCreate()
      setIsMutatingAccounts(false)
      return
    }

    try {
      const created = await createAccountRequest({
        code: input.code,
        name: input.name,
        is_active: true,
      })
      setAccounts((current) => sortAccounts([...current, created]))
      setIsLocalAccountsFallback(false)
    } catch (error) {
      if (shouldUseLocalAccountFallback(error)) {
        applyLocalCreate()
      } else {
        setErrorMessage(toErrorMessage(error))
      }
    } finally {
      setIsMutatingAccounts(false)
    }
  }

  async function handleUpdateAccount(accountId: string, input: { code: number; name: string }) {
    setErrorMessage(null)
    setIsMutatingAccounts(true)
    const applyLocalUpdate = () => {
      setAccounts((current) =>
        sortAccounts(
          current.map((account) =>
            account.id === accountId
              ? { ...account, code: input.code, name: input.name, updated_at: nowIso() }
              : account,
          ),
        ),
      )
      setIsLocalAccountsFallback(true)
    }

    if (isLocalAccountsFallback) {
      applyLocalUpdate()
      setIsMutatingAccounts(false)
      return
    }

    try {
      const updated = await updateAccountRequest(accountId, {
        code: input.code,
        name: input.name,
      })
      setAccounts((current) =>
        sortAccounts(current.map((account) => (account.id === accountId ? updated : account))),
      )
      setIsLocalAccountsFallback(false)
    } catch (error) {
      if (shouldUseLocalAccountFallback(error)) {
        applyLocalUpdate()
      } else {
        setErrorMessage(toErrorMessage(error))
      }
    } finally {
      setIsMutatingAccounts(false)
    }
  }

  async function handleRemoveAccount(accountId: string) {
    setErrorMessage(null)
    setIsMutatingAccounts(true)
    const applyLocalRemove = () => {
      setAccounts((current) => current.filter((account) => account.id !== accountId))
      setIsLocalAccountsFallback(true)
    }

    if (isLocalAccountsFallback) {
      applyLocalRemove()
      setIsMutatingAccounts(false)
      return
    }

    try {
      await removeAccountRequest(accountId)
      setAccounts((current) => current.filter((account) => account.id !== accountId))
      setIsLocalAccountsFallback(false)
    } catch (error) {
      if (shouldUseLocalAccountFallback(error)) {
        applyLocalRemove()
      } else {
        setErrorMessage(toErrorMessage(error))
      }
    } finally {
      setIsMutatingAccounts(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>Invoice to Journal Entry</h1>
        {screen !== 'home' ? (
          <div className="tab-row">
            {screen === 'invoice-review' ? (
              <button
                className="button-secondary"
                onClick={() => setScreen('invoice-management')}
                type="button"
              >
                Invoices
              </button>
            ) : null}
            <button className="button-secondary" onClick={() => setScreen('home')} type="button">
              Home
            </button>
          </div>
        ) : null}
      </header>

      {errorMessage !== null ? (
        <div className="flash flash--error" role="alert">
          {errorMessage}
        </div>
      ) : null}

      {screen === 'home' ? (
        <main className="home-grid">
          <button className="home-card" onClick={() => setScreen('invoice-management')} type="button">
            <h2>Invoice Management</h2>
          </button>
          <button className="home-card" onClick={() => setScreen('company-setup')} type="button">
            <h2>Company Setup</h2>
          </button>
        </main>
      ) : screen === 'invoice-management' ? (
        <main className="invoice-management-stack">
          <section className="invoice-management-top">
            <section className="card invoice-list-panel">
              <h2>Invoices</h2>

              <div className="invoice-list-group">
                <h3>Pending Review</h3>
                {pendingInvoices.length === 0 ? (
                  <p className="muted">No pending invoices.</p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Invoice</th>
                          <th>Status</th>
                          <th>Updated</th>
                          <th>Flag</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pendingInvoices.map((item) => {
                          const invoiceId = item.bundle.invoice.id
                          const status = getInvoiceStatus(item.bundle)
                          return (
                            <tr key={invoiceId}>
                              <td>{item.bundle.invoice.original_filename}</td>
                              <td>
                                <StatusPill status={status} />
                              </td>
                              <td>{formatTimestamp(item.updatedAt)}</td>
                              <td>
                                {item.duplicateOfInvoiceId === null
                                  ? '-'
                                  : `Possible duplicate of ${shortId(item.duplicateOfInvoiceId)}`}
                              </td>
                              <td>
                                <button
                                  className="button-secondary"
                                  onClick={() => {
                                    setSelectedInvoiceId(invoiceId)
                                    setScreen('invoice-review')
                                  }}
                                  type="button"
                                >
                                  Open
                                </button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="invoice-list-group">
                <h3>Processed Invoices</h3>
                {processedInvoices.length === 0 ? (
                  <p className="muted">No processed invoices.</p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Invoice</th>
                          <th>Status</th>
                          <th>Updated</th>
                          <th>Flag</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {processedInvoices.map((item) => {
                          const invoiceId = item.bundle.invoice.id
                          const status = getInvoiceStatus(item.bundle)
                          return (
                            <tr key={invoiceId}>
                              <td>{item.bundle.invoice.original_filename}</td>
                              <td>
                                <StatusPill status={status} />
                              </td>
                              <td>{formatTimestamp(item.updatedAt)}</td>
                              <td>
                                {item.duplicateOfInvoiceId === null
                                  ? '-'
                                  : `Possible duplicate of ${shortId(item.duplicateOfInvoiceId)}`}
                              </td>
                              <td>
                                <button
                                  className="button-secondary"
                                  onClick={() => {
                                    setSelectedInvoiceId(invoiceId)
                                    setScreen('invoice-review')
                                  }}
                                  type="button"
                                >
                                  Open
                                </button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>
            <InvoiceUploadPanel isUploading={isUploading} onUpload={handleUploadFiles} />
          </section>
        </main>
      ) : screen === 'invoice-review' ? (
        <main>
          {selectedBundle === null ? (
            <section className="card">
              <h2>Invoice Review</h2>
              <p className="muted">No invoice selected.</p>
              <div className="button-row">
                <button
                  className="button-secondary"
                  onClick={() => setScreen('invoice-management')}
                  type="button"
                >
                  Back to invoices
                </button>
              </div>
            </section>
          ) : (
            <section className="review-grid">
              <div className="left-column">
                <section className="card viewer-panel">
                  <h2>Invoice Viewer</h2>
                  {selectedPreviewUrl === null ? (
                    <p className="muted">No preview</p>
                  ) : (
                    <iframe src={selectedPreviewUrl} title="Uploaded invoice preview" />
                  )}
                </section>
              </div>

              <JournalReviewPanel
                accounts={activeAccounts}
                activeAccountIds={activeAccountIds}
                bundle={selectedBundle}
                isApproving={isApproving}
                isDeclining={isDeclining}
                isGenerating={isGenerating}
                isSavingEdits={isSavingJournalEdits}
                onApprove={handleApprove}
                onDecline={handleDecline}
                onGenerate={handleGenerate}
                onSaveEdits={handleSaveJournalEdits}
              />
            </section>
          )}
        </main>
      ) : (
        <main>
          <AccountsPanel
            accounts={accounts}
            isLoading={isLoadingAccounts}
            isMutating={isMutatingAccounts}
            onCreate={handleCreateAccount}
            onRefresh={refreshAccounts}
            onRemove={handleRemoveAccount}
            onUpdate={handleUpdateAccount}
          />
        </main>
      )}
    </div>
  )
}

export default App
