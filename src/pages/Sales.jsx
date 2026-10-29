import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CreditCard, Printer, Search, X } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { businessService } from '../services/businessService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { useAuth } from '../context/useAuth'
import { formatCurrency } from '../utils/formatters'
import ThermalPaymentReceipt from '../components/ThermalPaymentReceipt'

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
  const [selectedSale, setSelectedSale] = useState(null)
  const [payment, setPayment] = useState({ amount: '', payment_method: 'cash', reference_number: '', notes: '' })
  const [savingPayment, setSavingPayment] = useState(false)
  const [paymentReceipt, setPaymentReceipt] = useState(null)
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

  function openPayment(sale) {
    setPaymentReceipt(null)
    setSelectedSale(sale)
    setPayment({ amount: String(sale.outstanding_amount), payment_method: 'cash', reference_number: '', notes: '' })
  }

  async function submitPayment(event) {
    event.preventDefault()
    if (!selectedSale) return
    setSavingPayment(true)
    try {
      const recordedPayment = await commerceService.receiveSalePayment({ ...payment, sale_id: selectedSale.id })
      const [saleResult, businessResult] = await Promise.allSettled([
        commerceService.getSale(selectedSale.id),
        businessService.get(),
      ])
      const freshSale = saleResult.status === 'fulfilled'
        ? saleResult.value
        : {
          ...selectedSale,
          invoice_number: recordedPayment.invoice_number || selectedSale.invoice_number,
          total_amount: recordedPayment.total_amount ?? selectedSale.total_amount,
          paid_amount: recordedPayment.paid_amount ?? selectedSale.paid_amount,
          outstanding_amount: recordedPayment.outstanding_amount ?? selectedSale.outstanding_amount,
          payment_status: recordedPayment.payment_status ?? selectedSale.payment_status,
        }
      const business = businessResult.status === 'fulfilled' ? businessResult.value : null
      setPaymentReceipt({ sale: freshSale, payment: recordedPayment, business })
      setSelectedSale(null)
      setPayment({ amount: '', payment_method: 'cash', reference_number: '', notes: '' })
      setReload((value) => value + 1)
      notify('Payment recorded. A receipt is ready to print.')
      if (saleResult.status === 'rejected' || businessResult.status === 'rejected') {
        notify('Payment saved. Some receipt details could not be refreshed; the saved payment and balance are shown.', 'info')
      }
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSavingPayment(false)
    }
  }

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
        <thead><tr><th>Invoice</th><th>Customer</th><th>Date</th><th>Total</th><th>Paid</th><th>Outstanding</th>{canViewCosts && <><th>COGS</th><th>Gross profit</th></>}<th>Cashier</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>{loading ? <tr><td colSpan={canViewCosts ? 11 : 9} className="empty-cell">Loading sales…</td></tr> : items.length === 0 ? <tr><td colSpan={canViewCosts ? 11 : 9} className="empty-cell">No sales match your filters.</td></tr> : items.map((sale) => <tr key={sale.id}>
          <td><Link to={`/sales/${sale.id}`}><strong>{sale.invoice_number}</strong></Link></td><td>{sale.customer_name || 'Walk-in'}</td><td>{new Date(sale.sale_date).toLocaleString()}</td><td>{amount(sale.total_amount)}</td><td>{amount(sale.paid_amount)}</td><td>{amount(sale.outstanding_amount)}</td>{canViewCosts && <><td>{amount(sale.cogs_amount)}</td><td>{amount(sale.gross_profit)}</td></>}<td>{sale.cashier_name || '—'}</td><td><span className={`tag ${sale.payment_status === 'paid' ? 'success' : 'warning'}`}>{sale.payment_status}</span> <span className="tag neutral">{sale.status}</span></td><td>{Number(sale.outstanding_amount) > 0 && sale.status !== 'voided' ? <button type="button" className="ghost-button small" onClick={() => openPayment(sale)} aria-label={`Record payment for ${sale.invoice_number}`}><CreditCard size={14} />Receive payment</button> : '—'}</td>
        </tr>)}</tbody>
      </table></div>
        {total > 20 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pages}</span><button className="ghost-button" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
      {paymentReceipt && <section className="thermal-preview-section sales-payment-receipt" aria-label="Payment receipt preview">
        <div className="thermal-preview-heading"><div><span className="eyebrow">PAYMENT RECEIPT</span><h2>Receipt for {paymentReceipt.sale.invoice_number}</h2><p>This receipt records this payment and the remaining invoice balance.</p></div><div className="payment-receipt-actions"><button type="button" className="primary-button" onClick={() => window.print()}><Printer size={15} />Print receipt</button><button type="button" className="ghost-button" onClick={() => setPaymentReceipt(null)} aria-label="Close payment receipt"><X size={15} />Close</button></div></div>
        <ThermalPaymentReceipt {...paymentReceipt} cashierName={user?.name} amount={amount} />
      </section>}
      {selectedSale && <div className="modal-backdrop" onClick={() => !savingPayment && setSelectedSale(null)}><div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="sales-payment-title" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header"><h3 id="sales-payment-title">Record payment</h3><button type="button" className="ghost-button" disabled={savingPayment} onClick={() => setSelectedSale(null)}>Close</button></div>
        <form className="inventory-form" onSubmit={submitPayment}>
          <p>Invoice <strong>{selectedSale.invoice_number}</strong> · Outstanding <strong>{amount(selectedSale.outstanding_amount)}</strong></p>
          <label>Amount received<input required autoFocus type="number" min="0.01" max={selectedSale.outstanding_amount} step="0.01" value={payment.amount} onChange={(event) => setPayment({ ...payment, amount: event.target.value })} /></label>
          <label>Payment method<select value={payment.payment_method} onChange={(event) => setPayment({ ...payment, payment_method: event.target.value })}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="mobile_wallet">Mobile wallet</option><option value="other">Other</option></select></label>
          <label>Reference number<input value={payment.reference_number} maxLength="100" onChange={(event) => setPayment({ ...payment, reference_number: event.target.value })} /></label>
          <label>Notes<textarea rows={2} value={payment.notes} onChange={(event) => setPayment({ ...payment, notes: event.target.value })} /></label>
          <div className="modal-actions"><button type="button" className="ghost-button" disabled={savingPayment} onClick={() => setSelectedSale(null)}>Cancel</button><button className="primary-button" disabled={savingPayment}>{savingPayment ? 'Recording…' : 'Record payment & create receipt'}</button></div>
        </form>
      </div></div>}
    </div>
  )
}
