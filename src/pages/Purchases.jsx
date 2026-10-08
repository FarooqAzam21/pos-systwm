import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const amount = formatCurrency

export default function Purchases() {
  const [result, setResult] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const limit = 20
  const { notify } = useToast()
  useEffect(() => {
    let active = true
    commerceService.getPurchases({ search, page, limit })
      .then((data) => { if (active) setResult(data) })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [notify, search, page])
  const pageCount = Math.max(1, Math.ceil(result.total / limit))
  return (
    <div className="commerce-page">
      <div className="page-heading"><div><span className="eyebrow">INVENTORY INBOUND</span><h1>Purchases</h1><p>Record supplier invoices, payments, and incoming stock.</p></div><Link className="primary-button" to="/purchases/new"><Plus size={15} />New purchase</Link></div>
      <section className="panel commerce-panel">
        <div className="table-toolbar"><label className="search-input"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search purchase invoice" aria-label="Search purchases" /></label></div>
        <div className="data-table"><table><thead><tr><th>Invoice</th><th>Supplier</th><th>Date</th><th>Subtotal</th><th>Total</th><th>Paid</th><th>Outstanding</th><th>Status</th></tr></thead>
          <tbody>{loading ? <tr><td colSpan="8" className="empty-cell">Loading purchases…</td></tr> : result.items.length === 0 ? <tr><td colSpan="8" className="empty-cell">No purchases recorded yet.</td></tr> : result.items.map((purchase) => <tr key={purchase.id}>
            <td><Link to={`/purchases/${purchase.id}`}><strong>{purchase.invoice_number}</strong></Link></td><td>{purchase.supplier_name || '—'}</td><td>{purchase.purchase_date}</td><td>{amount(purchase.subtotal)}</td><td>{amount(purchase.total_amount)}</td><td>{amount(purchase.paid_amount)}</td><td>{amount(purchase.outstanding_amount)}</td><td><span className={`tag ${purchase.payment_status === 'paid' ? 'success' : 'warning'}`}>{purchase.payment_status}</span></td>
          </tr>)}</tbody>
        </table></div>
        {result.total > limit && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount} · {result.total} purchases</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
