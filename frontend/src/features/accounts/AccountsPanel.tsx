import { useMemo, useState } from 'react'
import { useEffect } from 'react'
import type { FormEvent } from 'react'

import type { Account } from '../../lib/types/api'

interface AccountDraft {
  code: string
  name: string
}

interface AccountsPanelProps {
  accounts: Account[]
  isMutating: boolean
  isLoading: boolean
  onSaveSnapshot: (input: { code: number; name: string }[]) => Promise<Account[]>
  onUnsavedChangesChange?: (hasUnsavedChanges: boolean) => void
}

interface EditableAccount {
  id: string
  code: string
  name: string
}

const DRAFT_ACCOUNT_ID_PREFIX = 'draft-account-'

function toEditableAccount(account: Account): EditableAccount {
  return {
    id: account.id,
    code: String(account.code),
    name: account.name,
  }
}

function toActiveEditableAccounts(accounts: Account[]): EditableAccount[] {
  return [...accounts]
    .filter((account) => account.is_active)
    .sort((left, right) => left.code - right.code)
    .map(toEditableAccount)
}

function sortedEditableAccounts(accounts: EditableAccount[]): EditableAccount[] {
  return [...accounts].sort((left, right) => {
    const leftCode = Number(left.code)
    const rightCode = Number(right.code)
    if (Number.isFinite(leftCode) && Number.isFinite(rightCode)) {
      if (leftCode !== rightCode) {
        return leftCode - rightCode
      }
    }
    return left.id.localeCompare(right.id)
  })
}

function normalizeForComparison(accounts: EditableAccount[]): string {
  return JSON.stringify(
    sortedEditableAccounts(accounts).map((account) => ({
      id: account.id,
      code: account.code.trim(),
      name: account.name.trim(),
    })),
  )
}

export function AccountsPanel({
  accounts,
  isMutating,
  isLoading,
  onSaveSnapshot,
  onUnsavedChangesChange,
}: AccountsPanelProps) {
  const activeEditableAccounts = useMemo(
    () => toActiveEditableAccounts(accounts),
    [accounts],
  )

  const [createDraft, setCreateDraft] = useState<AccountDraft>({ code: '', name: '' })
  const [baselineAccounts, setBaselineAccounts] = useState<EditableAccount[]>(
    activeEditableAccounts,
  )
  const [workingAccounts, setWorkingAccounts] = useState<EditableAccount[]>(
    activeEditableAccounts,
  )
  const [editAccountId, setEditAccountId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<AccountDraft>({ code: '', name: '' })
  const [localError, setLocalError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  const hasUnsavedChanges = useMemo(() => {
    return (
      normalizeForComparison(workingAccounts) !== normalizeForComparison(baselineAccounts)
    )
  }, [baselineAccounts, workingAccounts])

  useEffect(() => {
    onUnsavedChangesChange?.(hasUnsavedChanges)
  }, [hasUnsavedChanges, onUnsavedChangesChange])

  useEffect(() => {
    if (!hasUnsavedChanges) {
      return
    }
    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
    }
  }, [hasUnsavedChanges])

  function parseDraft(draft: AccountDraft): { code: number; name: string } | null {
    const code = Number(draft.code)
    const name = draft.name.trim()
    if (!Number.isInteger(code) || code <= 0) {
      setLocalError('Account code must be a positive number.')
      return null
    }
    if (name === '') {
      setLocalError('Account name is required.')
      return null
    }
    return { code, name }
  }

  function validateWorkingAccounts(entries: EditableAccount[]): string | null {
    const usedCodes = new Set<number>()
    const usedNames = new Set<string>()
    for (const entry of entries) {
      const code = Number(entry.code)
      const name = entry.name.trim()
      if (!Number.isInteger(code) || code <= 0) {
        return 'Each account code must be a positive number.'
      }
      if (name === '') {
        return 'Each account name is required.'
      }
      if (usedCodes.has(code)) {
        return `Duplicate account code in unsaved changes: ${code}.`
      }
      usedCodes.add(code)

      const normalizedName = name.toLowerCase()
      if (usedNames.has(normalizedName)) {
        return `Duplicate account name in unsaved changes: ${name}.`
      }
      usedNames.add(normalizedName)
    }
    return null
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLocalError(null)
    setSaveMessage(null)
    const parsed = parseDraft(createDraft)
    if (parsed === null) {
      return
    }
    const draftId = `${DRAFT_ACCOUNT_ID_PREFIX}${crypto.randomUUID()}`
    setWorkingAccounts((current) =>
      sortedEditableAccounts([
        ...current,
        {
          id: draftId,
          code: String(parsed.code),
          name: parsed.name,
        },
      ]),
    )
    setCreateDraft({ code: '', name: '' })
  }

  async function handleSaveEdit(accountId: string) {
    setLocalError(null)
    setSaveMessage(null)
    const parsed = parseDraft(editDraft)
    if (parsed === null) {
      return
    }
    setWorkingAccounts((current) =>
      sortedEditableAccounts(
        current.map((account) =>
          account.id === accountId
            ? { ...account, code: String(parsed.code), name: parsed.name }
            : account,
        ),
      ),
    )
    setEditAccountId(null)
  }

  async function handleCommitChanges() {
    setLocalError(null)
    setSaveMessage(null)

    const validationError = validateWorkingAccounts(workingAccounts)
    if (validationError !== null) {
      setLocalError(validationError)
      return
    }

    if (!hasUnsavedChanges) {
      setSaveMessage('No changes to save.')
      return
    }

    const snapshotInput = sortedEditableAccounts(workingAccounts).map((account) => ({
      code: Number(account.code),
      name: account.name.trim(),
    }))

    try {
      const refreshedAccounts = await onSaveSnapshot(snapshotInput)
      const refreshedEditable = toActiveEditableAccounts(refreshedAccounts)
      setBaselineAccounts(refreshedEditable)
      setWorkingAccounts(refreshedEditable)
      setEditAccountId(null)
      setSaveMessage('Chart of accounts saved.')
    } catch (error) {
      if (error instanceof Error && error.message.trim() !== '') {
        setLocalError(error.message)
        return
      }
      setLocalError('Failed to save chart of accounts.')
    }
  }

  return (
    <section className="card accounts-panel">
      <div className="review-header">
        <h2>Chart of Accounts</h2>
      </div>

      <form className="accounts-create-form" onSubmit={(event) => void handleCreate(event)}>
        <label>
          Code
          <input
            inputMode="numeric"
            placeholder="e.g. 6530"
            type="text"
            value={createDraft.code}
            onChange={(event) => setCreateDraft((current) => ({ ...current, code: event.target.value }))}
          />
        </label>
        <label>
          Name
          <input
            placeholder="Account name"
            type="text"
            value={createDraft.name}
            onChange={(event) => setCreateDraft((current) => ({ ...current, name: event.target.value }))}
          />
        </label>
        <button disabled={isMutating} type="submit">
          Add account
        </button>
      </form>

      <div className="button-row">
        <button
          disabled={isMutating || isLoading || !hasUnsavedChanges}
          onClick={() => void handleCommitChanges()}
          type="button"
        >
          {isMutating ? 'Saving...' : 'Save changes'}
        </button>
        {saveMessage !== null ? <p className="small-muted">{saveMessage}</p> : null}
      </div>

      {localError !== null ? (
        <div className="flash flash--error" role="alert">
          {localError}
        </div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedEditableAccounts(workingAccounts).map((account) => {
              const isEditing = editAccountId === account.id
              return (
                <tr key={account.id}>
                  <td>
                    {isEditing ? (
                      <input
                        className="table-input"
                        inputMode="numeric"
                        type="text"
                        value={editDraft.code}
                        onChange={(event) =>
                          setEditDraft((current) => ({ ...current, code: event.target.value }))
                        }
                      />
                    ) : (
                      account.code
                    )}
                  </td>
                  <td>
                    {isEditing ? (
                      <input
                        className="table-input"
                        type="text"
                        value={editDraft.name}
                        onChange={(event) =>
                          setEditDraft((current) => ({ ...current, name: event.target.value }))
                        }
                      />
                    ) : (
                      account.name
                    )}
                  </td>
                  <td>
                    <div className="action-row">
                      {isEditing ? (
                        <>
                          <button
                            className="button-secondary"
                            disabled={isMutating}
                            onClick={() => void handleSaveEdit(account.id)}
                            type="button"
                          >
                            Save
                          </button>
                          <button
                            className="button-secondary"
                            disabled={isMutating}
                            onClick={() => setEditAccountId(null)}
                            type="button"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className="button-secondary"
                            disabled={isMutating || isLoading}
                            onClick={() => {
                              setEditAccountId(account.id)
                              setEditDraft({
                                code: account.code,
                                name: account.name,
                              })
                            }}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            className="button-secondary button-danger"
                            disabled={isMutating || isLoading}
                            onClick={() => {
                              setSaveMessage(null)
                              setWorkingAccounts((current) =>
                                current.filter((entry) => entry.id !== account.id),
                              )
                              if (editAccountId === account.id) {
                                setEditAccountId(null)
                              }
                            }}
                            type="button"
                          >
                            Remove
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
