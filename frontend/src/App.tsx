import { useCallback, useEffect, useMemo, useState } from 'react'

import './App.css'
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
  updateAccount as updateAccountRequest,
  uploadInvoice,
} from './lib/api/client'
import type { Account, InvoiceBundle } from './lib/types/api'

type Screen = 'review' | 'accounts'

const ACCOUNT_FALLBACK_STATUS_CODES = new Set([404, 405, 500, 501, 502, 503])

function sortAccounts(accounts: Account[]): Account[] {
  return [...accounts].sort((left, right) => left.code - right.code)
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

function App() {
  const [screen, setScreen] = useState<Screen>('review')
  const [bundle, setBundle] = useState<InvoiceBundle | null>(null)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null)
  const [isLocalAccountsFallback, setIsLocalAccountsFallback] = useState(false)

  const [isUploading, setIsUploading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [isDeclining, setIsDeclining] = useState(false)
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false)
  const [isMutatingAccounts, setIsMutatingAccounts] = useState(false)

  const activeAccountIds = useMemo(() => {
    return new Set(accounts.map((account) => account.id))
  }, [accounts])

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
    return () => {
      if (pdfPreviewUrl !== null) {
        URL.revokeObjectURL(pdfPreviewUrl)
      }
    }
  }, [pdfPreviewUrl])

  async function handleUpload(file: File) {
    setErrorMessage(null)
    setIsUploading(true)

    try {
      const result = await uploadInvoice(file)
      setBundle(result)

      const nextUrl = URL.createObjectURL(file)
      setPdfPreviewUrl((current) => {
        if (current !== null) {
          URL.revokeObjectURL(current)
        }
        return nextUrl
      })
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setIsUploading(false)
    }
  }

  async function handleGenerate() {
    if (bundle === null) {
      return
    }

    setErrorMessage(null)
    setIsGenerating(true)

    try {
      const result = await generateJournalEntry(bundle.invoice.id)
      setBundle(result)
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleApprove() {
    const entryId = bundle?.journal_entry?.id
    if (entryId === undefined) {
      return
    }

    setErrorMessage(null)
    setIsApproving(true)

    try {
      const updatedEntry = await approveJournalEntry(entryId)
      setBundle((current) => {
        if (current === null) {
          return current
        }
        return {
          ...current,
          journal_entry: updatedEntry,
        }
      })
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setIsApproving(false)
    }
  }

  async function handleDecline(reason: string) {
    const entryId = bundle?.journal_entry?.id
    if (entryId === undefined) {
      return
    }

    setErrorMessage(null)
    setIsDeclining(true)

    try {
      const updatedEntry = await declineJournalEntry(entryId, reason)
      setBundle((current) => {
        if (current === null) {
          return current
        }
        return {
          ...current,
          journal_entry: updatedEntry,
        }
      })
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
      const created = await createAccountRequest({ code: input.code, name: input.name, is_active: true })
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
      const updated = await updateAccountRequest(accountId, { code: input.code, name: input.name })
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
        <nav className="tab-row" aria-label="Primary navigation">
          <button
            className={screen === 'review' ? 'tab tab--active' : 'tab'}
            onClick={() => setScreen('review')}
            type="button"
          >
            Review
          </button>
          <button
            className={screen === 'accounts' ? 'tab tab--active' : 'tab'}
            onClick={() => setScreen('accounts')}
            type="button"
          >
            Chart of Accounts
          </button>
        </nav>
      </header>

      {errorMessage !== null ? (
        <div className="flash flash--error" role="alert">
          {errorMessage}
        </div>
      ) : null}

      {screen === 'review' ? (
        <main className="review-grid">
          <div className="left-column">
            <InvoiceUploadPanel
              canGenerate={bundle !== null}
              isGenerating={isGenerating}
              isUploading={isUploading}
              onGenerate={handleGenerate}
              onUpload={handleUpload}
            />

            <section className="card viewer-panel">
              <h2>Invoice Viewer</h2>
              {pdfPreviewUrl === null ? (
                <p className="muted">No preview</p>
              ) : (
                <iframe src={pdfPreviewUrl} title="Uploaded invoice preview" />
              )}
            </section>

            {bundle?.invoice.extracted_text !== null && bundle?.invoice.extracted_text !== undefined ? (
              <section className="card extracted-panel">
                <h2>Extracted Markdown</h2>
                <pre>{bundle.invoice.extracted_text}</pre>
              </section>
            ) : null}
          </div>

          <JournalReviewPanel
            activeAccountIds={activeAccountIds}
            bundle={bundle}
            isApproving={isApproving}
            isDeclining={isDeclining}
            onApprove={handleApprove}
            onDecline={handleDecline}
          />
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
