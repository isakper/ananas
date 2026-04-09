import { useMemo, useState } from 'react'
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
  onCreate: (input: { code: number; name: string }) => Promise<void>
  onRefresh: () => Promise<void>
  onRemove: (accountId: string) => Promise<void>
  onUpdate: (accountId: string, input: { code: number; name: string }) => Promise<void>
}

function toDraft(account: Account): AccountDraft {
  return {
    code: String(account.code),
    name: account.name,
  }
}

export function AccountsPanel({
  accounts,
  isMutating,
  isLoading,
  onCreate,
  onRefresh,
  onRemove,
  onUpdate,
}: AccountsPanelProps) {
  const [createDraft, setCreateDraft] = useState<AccountDraft>({ code: '', name: '' })
  const [editAccountId, setEditAccountId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<AccountDraft>({ code: '', name: '' })
  const [localError, setLocalError] = useState<string | null>(null)

  const sortedAccounts = useMemo(() => {
    return [...accounts].sort((left, right) => left.code - right.code)
  }, [accounts])

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

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLocalError(null)
    const parsed = parseDraft(createDraft)
    if (parsed === null) {
      return
    }
    await onCreate(parsed)
    setCreateDraft({ code: '', name: '' })
  }

  async function handleSaveEdit(accountId: string) {
    setLocalError(null)
    const parsed = parseDraft(editDraft)
    if (parsed === null) {
      return
    }
    await onUpdate(accountId, parsed)
    setEditAccountId(null)
  }

  return (
    <section className="card accounts-panel">
      <div className="review-header">
        <h2>Chart of Accounts</h2>
        <button
          className="button-secondary"
          disabled={isLoading || isMutating}
          onClick={() => void onRefresh()}
          type="button"
        >
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
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
            {sortedAccounts.map((account) => {
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
                            disabled={isMutating}
                            onClick={() => {
                              setEditAccountId(account.id)
                              setEditDraft(toDraft(account))
                            }}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            className="button-secondary button-danger"
                            disabled={isMutating}
                            onClick={() => void onRemove(account.id)}
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
