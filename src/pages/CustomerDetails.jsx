import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CreditCard } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const currency = formatCurrency

export default function CustomerDetails() {
  const { customerId } = useParams()
  const [customer, setCustomer] = useState(null)
  const [showPayment, setShowPayment] = useState(false)
  const [payment, setPayment] = useState({ amount: '', payment_method: 'cash', reference_number: '', notes: '' })
  const [saving, setSaving] = useState(false)
  const [reload, setReload] = useState(0)
  const { notify } = useToast()

  useEffect(() => {
    let active = true
    commerceService.getCustomer(customerId).then((data) => { if (active) setCustomer(data) }).catch((error) => notify(getApiErrorMessage(error), 'error'))
    return () => { active = false }
  }, [customerId, reload, notify])

  async function receivePayment(event) {
    event.preventDefault()
    setSaving(true)
    try {
      await commerceService.receiveCustomerPayment({ ...payment, customer_id: customerId })
      notify('Customer payment recorded.')
      setShowPayment(false)
      setPayment({ amount: '', payment_method: 'cash', reference_number: '', notes: '' })
      setReload((value) => value + 1)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSaving(false)
    }
  }

  if (!customer) return <div className="panel skeleton" style={{ minHeight: 240 }} />
  return (
    <div className="commerce-page">
      <div className="page-heading"><div><Link className="back-link" to="/customers"><ArrowLeft size={14} />Customers</Link><span className="eyebrow">CUSTOMER ACCOUNT</span><h1>{customer.name}</h1><p>{[customer.phone, customer.email].filter(Boolean).join(' · ') || 'Customer details and transaction history'}</p></div>
        {Number(customer.current_balance) > 0 && <button className="primary-button" onClick={() => setShowPayment(true)}><CreditCard size={15} />Receive payment</button>}
      </div>
      <section className="kpi-grid commerce-kpis">
        <article className="kpi-card"><div className="kpi-copy"><span>Total purchases</span><strong>{currency(customer.total_purchases)}</strong></div></article>
        <article className="kpi-card"><div className="kpi-copy"><span>Payments received</span><strong>{currency(customer.total_paid)}</strong></div></article>
        <article className="kpi-card"><div className="kpi-copy"><span>Outstanding balance</span><strong>{currency(customer.current_balance)}</strong></div></article>
        <article className="kpi-card"><div className="kpi-copy"><span>Transactions</span><strong>{customer.transaction_count || 0}</strong></div></article>
      </section>
      <section className="panel commerce-panel">
        <div className="panel-heading"><div><h2>Sales history</h2><p>Recorded sales and remaining balances.</p></div></div>
        <div className="data-table"><table><thead><tr><th>Invoice</th><th>Date</th><th>Total</th><th>Paid</th><th>Outstanding</th><th>Payment</th><th>Sale status</th></tr></thead>
          <tbody>{customer.sales?.length ? customer.sales.map((sale) => <tr key={sale.id}><td><Link to={`/sales/${sale.id}`}>{sale.invoice_number}</Link></td><td>{new Date(sale.sale_date).toLocaleString()}</td><td>{currency(sale.total_amount)}</td><td>{currency(sale.paid_amount)}</td><td>{currency(sale.outstanding_amount)}</td><td>{sale.payment_status}</td><td>{sale.status}</td></tr>) : <tr><td colSpan="7" className="empty-cell">No sales recorded for this customer.</td></tr>}</tbody>
        </table></div>
      </section>
      <section className="panel commerce-panel"><div className="panel-heading"><div><h2>Payment history</h2><p>Incoming payments and refunds.</p></div></div>
        <div className="data-table"><table><thead><tr><th>Date</th><th>Direction</th><th>Method</th><th>Amount</th><th>Reference</th></tr></thead>
          <tbody>{customer.payments?.length ? customer.payments.map((item) => <tr key={item.id}><td>{new Date(item.payment_date).toLocaleString()}</td><td>{item.payment_type}</td><td>{item.payment_method}</td><td>{currency(item.amount)}</td><td>{item.reference_number || item.reference_id}</td></tr>) : <tr><td colSpan="5" className="empty-cell">No payments recorded.</td></tr>}</tbody>
        </table></div>
      </section>
      <section className="panel commerce-panel"><div className="panel-heading"><div><h2>Returns</h2><p>Refunds associated with this customer’s sales.</p></div></div>
        <div className="data-table"><table><thead><tr><th>Date</th><th>Invoice</th><th>Returned products</th><th>Refund</th></tr></thead>
          <tbody>{customer.returns?.length ? customer.returns.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td><Link to={`/sales/${item.sale_id}`}>{item.invoice_number || 'View sale'}</Link></td><td>{item.items?.map((line) => `${line.product_name} × ${line.quantity}`).join(', ') || '—'}</td><td>{currency(item.refund_amount)}</td></tr>) : <tr><td colSpan="4" className="empty-cell">No returns recorded.</td></tr>}</tbody>
        </table></div>
      </section>
      {showPayment && <div className="modal-backdrop" onClick={() => setShowPayment(false)}><div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header"><h3>Receive customer payment</h3><button className="ghost-button" onClick={() => setShowPayment(false)}>Close</button></div>
        <form className="inventory-form" onSubmit={receivePayment}>
          <p>Outstanding balance: <strong>{currency(customer.current_balance)}</strong></p>
          <label>Amount<input required type="number" min="0.01" max={customer.current_balance} step="0.01" value={payment.amount} onChange={(event) => setPayment({ ...payment, amount: event.target.value })} /></label>
          <label>Payment method<select value={payment.payment_method} onChange={(event) => setPayment({ ...payment, payment_method: event.target.value })}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="mobile_wallet">Mobile wallet</option><option value="other">Other</option></select></label>
          <label>Reference number<input value={payment.reference_number} onChange={(event) => setPayment({ ...payment, reference_number: event.target.value })} /></label>
          <label>Notes<textarea rows={2} value={payment.notes} onChange={(event) => setPayment({ ...payment, notes: event.target.value })} /></label>
          <div className="modal-actions"><button type="button" className="ghost-button" onClick={() => setShowPayment(false)}>Cancel</button><button className="primary-button" disabled={saving}>{saving ? 'Recording…' : 'Record payment'}</button></div>
        </form>
      </div></div>}
    </div>
  )
}
