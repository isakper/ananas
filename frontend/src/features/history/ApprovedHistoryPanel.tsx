import type { ApprovedHistoryItem } from '../../lib/types/history'

interface ApprovedHistoryPanelProps {
  entries: ApprovedHistoryItem[]
}

function formatMoney(value: string, currency: string): string {
  const parsed = Number(value)
  if (Number.isFinite(parsed)) {
    return `${parsed.toFixed(2)} ${currency}`
  }
  return `${value} ${currency}`
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.valueOf())) {
    return value
  }
  return parsed.toLocaleString()
}

export function ApprovedHistoryPanel({ entries }: ApprovedHistoryPanelProps) {
  return (
    <section className="card history-panel">
      <h2>Accepted Entries</h2>
      {entries.length === 0 ? (
        <p className="muted">No accepted entries.</p>
      ) : (
        <div className="history-list">
          {entries.map((entry) => (
            <article className="history-item" key={entry.journalEntryId}>
              <header className="history-item-header">
                <strong>{entry.invoiceFilename}</strong>
                <span>{formatTimestamp(entry.approvedAt)}</span>
              </header>
              <div className="history-meta">
                <span>{`Debit ${formatMoney(entry.totalDebit, entry.currency)}`}</span>
                <span>{`Credit ${formatMoney(entry.totalCredit, entry.currency)}`}</span>
              </div>
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
                      <tr key={`${entry.journalEntryId}-${posting.lineNo}`}>
                        <td>{posting.lineNo}</td>
                        <td>{posting.account}</td>
                        <td>{posting.description ?? '-'}</td>
                        <td>{formatMoney(posting.debit, entry.currency)}</td>
                        <td>{formatMoney(posting.credit, entry.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
