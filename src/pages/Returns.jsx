import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const amount = formatCurrency

export default function Returns() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const { notify } = useToast()

  useEffect(() => {
    let active = true
    commerceService.getReturns({ search, page, limit: 20 })
      .then((data) => {
        if (active) {
          setItems(data.items)
          setTotal(data.total)
        }
      })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [page, search, notify])

  const pages = Math.max(1, Math.ceil(total / 20))

  return (
    <div className="commerce-page">
      <div className="page-heading"><div><span className="eyebrow">TRANSACTIONS</span><h1>Returns</h1><p>Refunds and returned items recorded for this business.</p></div></div>
      <section className="panel commerce-panel">
        <div className="table-toolbar"><label className="search-input"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search invoice or return notes" aria-label="Search returns" /></label></div>
        <div className="data-table"><table>
          <thead><tr><th>Date</th><th>Sale invoice</th><th>Returned lines</th><th>Refund</th><th>Reason / notes</th></tr></thead>
          <tbody>
            {loading ? <tr><td colSpan="5" className="empty-cell">Loading returns…</td></tr>
              : items.length === 0 ? <tr><td colSpan="5" className="empty-cell">No returns have been recorded.</td></tr>
                : items.map((record) => <tr key={record.id}>
                  <td>{new Date(record.created_at).toLocaleString()}</td>
                  <td><Link to={`/sales/${record.sale_id}`}><strong>{record.invoice_number || 'View sale'}</strong></Link></td>
                  <td>{record.items.reduce((sum, item) => sum + Number(item.quantity), 0)} units</td>
                  <td>{amount(record.refund_amount)}</td>
                  <td>{record.notes || '—'}</td>
                </tr>)}
          </tbody>
        </table></div>
        {total > 20 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pages}</span><button className="ghost-button" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
