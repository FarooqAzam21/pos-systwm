import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const amount = formatCurrency

export default function Payments() {
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const limit = 20
  const { notify } = useToast()
  useEffect(() => {
    let active = true
    commerceService.getPayments({ limit: 200 })
      .then((data) => { if (active) setPayments(data) })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [notify])
  const filtered = payments.filter((payment) => `${payment.payment_type} ${payment.invoice_number || ''} ${payment.reference_type || ''} ${payment.customer_name || ''} ${payment.supplier_name || ''} ${payment.payment_method || ''} ${payment.reference_number || ''} ${payment.received_by_name || ''}`.toLowerCase().includes(search.trim().toLowerCase()))
  const pageCount = Math.max(1, Math.ceil(filtered.length / limit))
  const pageItems = filtered.slice((page - 1) * limit, page * limit)
  return <div className="commerce-page">
    <div className="page-heading"><div><span className="eyebrow">CASH FLOW</span><h1>Payments</h1><p>Recorded sale receipts, supplier payments, and refunds.</p></div></div>
    <section className="panel commerce-panel"><div className="table-toolbar"><label className="search-input"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search payments, references, customers" aria-label="Search payments" /></label></div><div className="data-table"><table><thead><tr><th>Date</th><th>Direction</th><th>Reference</th><th>Customer / Supplier</th><th>Method</th><th>Amount</th><th>Reference number</th><th>Received by</th></tr></thead>
      <tbody>{loading ? <tr><td colSpan="8" className="empty-cell">Loading payments…</td></tr> : filtered.length === 0 ? <tr><td colSpan="8" className="empty-cell">No payments match your search.</td></tr> : pageItems.map((payment) => <tr key={payment.id}><td>{new Date(payment.payment_date).toLocaleString()}</td><td>{payment.payment_type}</td><td>{payment.invoice_number || payment.reference_type}</td><td>{payment.customer_name || payment.supplier_name || '—'}</td><td>{payment.payment_method}</td><td>{amount(payment.amount)}</td><td>{payment.reference_number || '—'}</td><td>{payment.received_by_name || '—'}</td></tr>)}</tbody>
    </table></div>{filtered.length > limit && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount} · {filtered.length} payments</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}</section>
  </div>
}
