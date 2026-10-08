import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { useAuth } from '../context/useAuth'
import { formatCurrency } from '../utils/formatters'

const amount = formatCurrency

export default function Sales() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  const { notify } = useToast()
  const { user } = useAuth()
  const canViewCosts = user?.role !== 'Cashier'
  useEffect(() => {
    let active = true
    setLoading(true)
    commerceService.getSales({ search, payment_status: status, start_date: startDate, end_date: endDate, page, limit: 20 })
      .then((data) => { if (active) { setItems(data.items); setTotal(data.total) } })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [search, status, startDate, endDate, page, reload, notify])
  const pages = Math.max(1, Math.ceil(total / 20))
  return (
    <div className="commerce-page">
      <div className="page-heading"><div><span className="eyebrow">TRANSACTIONS</span><h1>Sales</h1><p>{canViewCosts ? 'Sales history, payments, balances, COGS, and gross profit.' : 'Sales history, payments, and customer balances.'}</p></div><Link className="primary-button" to="/pos">New sale</Link></div>
      <div className="commerce-toolbar sale-filters">
        <div className="search-input"><Search size={15} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search invoice or customer" /></div>
        <select className="filter-select" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="">All payment statuses</option><option value="paid">Paid</option><option value="partial">Partial</option><option value="unpaid">Unpaid</option></select>
        <label className="date-field">From<input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setPage(1) }} /></label>
        <label className="date-field">To<input type="date" value={endDate} onChange={(event) => { setEndDate(event.target.value); setPage(1) }} /></label>
      </div>
      <section className="panel commerce-panel"><div className="data-table"><table>
        <thead><tr><th>Invoice</th><th>Customer</th><th>Date</th><th>Total</th><th>Paid</th><th>Outstanding</th>{canViewCosts && <><th>COGS</th><th>Gross profit</th></>}<th>Cashier</th><th>Status</th></tr></thead>
        <tbody>{loading ? <tr><td colSpan={canViewCosts ? 10 : 8} className="empty-cell">Loading sales…</td></tr> : items.length === 0 ? <tr><td colSpan={canViewCosts ? 10 : 8} className="empty-cell">No sales match your filters.</td></tr> : items.map((sale) => <tr key={sale.id}>
          <td><Link to={`/sales/${sale.id}`}><strong>{sale.invoice_number}</strong></Link></td><td>{sale.customer_name || 'Walk-in'}</td><td>{new Date(sale.sale_date).toLocaleString()}</td><td>{amount(sale.total_amount)}</td><td>{amount(sale.paid_amount)}</td><td>{amount(sale.outstanding_amount)}</td>{canViewCosts && <><td>{amount(sale.cogs_amount)}</td><td>{amount(sale.gross_profit)}</td></>}<td>{sale.cashier_name || '—'}</td><td><span className={`tag ${sale.payment_status === 'paid' ? 'success' : 'warning'}`}>{sale.payment_status}</span> <span className="tag neutral">{sale.status}</span></td>
        </tr>)}</tbody>
      </table></div>
        {total > 20 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pages}</span><button className="ghost-button" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
