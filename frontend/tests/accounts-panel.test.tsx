import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { AccountsPanel } from '../src/features/accounts/AccountsPanel'
import type { Account } from '../src/lib/types/api'

function makeAccount(id: string, code: number, name: string): Account {
  return {
    id,
    code,
    name,
    is_active: true,
    created_at: '2026-04-10T08:00:00.000Z',
    updated_at: '2026-04-10T08:00:00.000Z',
  }
}

describe('AccountsPanel draft workflow', () => {
  it('supports add/edit/remove and save snapshot', async () => {
    const user = userEvent.setup()
    const onSaveSnapshot = vi.fn().mockResolvedValue([
      makeAccount('a-1', 1000, 'Cash account'),
      makeAccount('a-3', 3000, 'Office supplies'),
    ])

    render(
      <AccountsPanel
        accounts={[makeAccount('a-1', 1000, 'Cash'), makeAccount('a-2', 2000, 'Revenue')]}
        isLoading={false}
        isMutating={false}
        onSaveSnapshot={onSaveSnapshot}
      />,
    )

    await user.type(screen.getByLabelText('Code'), '3000')
    await user.type(screen.getByLabelText('Name'), 'Office supplies')
    await user.click(screen.getByRole('button', { name: 'Add account' }))

    const cashRow = screen.getByText('Cash').closest('tr')
    expect(cashRow).not.toBeNull()
    if (cashRow === null) {
      throw new Error('Cash row missing')
    }

    await user.click(within(cashRow).getByRole('button', { name: 'Edit' }))

    await user.clear(within(cashRow).getByDisplayValue('1000'))
    await user.type(within(cashRow).getByDisplayValue(''), '1000')
    await user.clear(within(cashRow).getByDisplayValue('Cash'))
    await user.type(within(cashRow).getByDisplayValue(''), 'Cash account')
    await user.click(within(cashRow).getByRole('button', { name: 'Save' }))

    const revenueRow = screen.getByText('Revenue').closest('tr')
    expect(revenueRow).not.toBeNull()
    if (revenueRow === null) {
      throw new Error('Revenue row missing')
    }
    await user.click(within(revenueRow).getByRole('button', { name: 'Remove' }))

    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => {
      expect(onSaveSnapshot).toHaveBeenCalledTimes(1)
    })

    expect(onSaveSnapshot).toHaveBeenCalledWith([
      { code: 1000, name: 'Cash account' },
      { code: 3000, name: 'Office supplies' },
    ])

    expect(screen.getByText('Chart of accounts saved.')).toBeInTheDocument()
  })

  it('keeps draft state and shows sync error when save snapshot fails', async () => {
    const user = userEvent.setup()
    const onUnsavedChangesChange = vi.fn()
    const onSaveSnapshot = vi
      .fn()
      .mockRejectedValue(
        new Error('Chart of accounts saved, but failed to sync latest state. Request failed (503)'),
      )

    render(
      <AccountsPanel
        accounts={[makeAccount('a-1', 1000, 'Cash')]}
        isLoading={false}
        isMutating={false}
        onSaveSnapshot={onSaveSnapshot}
        onUnsavedChangesChange={onUnsavedChangesChange}
      />,
    )

    await user.type(screen.getByLabelText('Code'), '3000')
    await user.type(screen.getByLabelText('Name'), 'Office supplies')
    await user.click(screen.getByRole('button', { name: 'Add account' }))
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(
      await screen.findByText('Chart of accounts saved, but failed to sync latest state. Request failed (503)'),
    ).toBeInTheDocument()

    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled()
    expect(onUnsavedChangesChange).toHaveBeenLastCalledWith(true)
  })

  it('registers unsaved-leave warning when draft has unsaved changes', async () => {
    const user = userEvent.setup()
    const onUnsavedChangesChange = vi.fn()

    render(
      <AccountsPanel
        accounts={[makeAccount('a-1', 1000, 'Cash')]}
        isLoading={false}
        isMutating={false}
        onSaveSnapshot={vi.fn().mockResolvedValue([makeAccount('a-1', 1000, 'Cash')])}
        onUnsavedChangesChange={onUnsavedChangesChange}
      />,
    )

    await user.type(screen.getByLabelText('Code'), '3000')
    await user.type(screen.getByLabelText('Name'), 'Office supplies')
    await user.click(screen.getByRole('button', { name: 'Add account' }))

    const beforeUnloadEvent = new Event('beforeunload', { cancelable: true })
    Object.defineProperty(beforeUnloadEvent, 'returnValue', {
      configurable: true,
      writable: true,
      value: undefined,
    })

    window.dispatchEvent(beforeUnloadEvent)

    expect(beforeUnloadEvent.defaultPrevented).toBe(true)
    expect((beforeUnloadEvent as BeforeUnloadEvent).returnValue).toBe('')
    expect(onUnsavedChangesChange).toHaveBeenLastCalledWith(true)
  })
})
