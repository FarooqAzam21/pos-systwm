import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CreditCard } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const amount = formatCurrency

export default function PurchaseDetails() {
  const { purchaseId } = useParams()
  const [purchase, setPurchase] = useState(null)
  const [payment, setPayment] = useState({ amount: '', payment_method: 'cash', reference_number: '', notes: '' })
  const [showPayment, setShowPayment] = useState(false)
  const [saving, setSaving] = useState(false)
  const [reload, setReload] = useState(0)
  const { notify } = useToast()

  useEffect(() => {
    let active = true
    commerceService.getPurchase(purchaseId)
      .then((data) => { if (active) setPurchase(data) })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
    return () => { active = false }
  }, [purchaseId, reload, notify])

  async function submitPayment(event) {
    event.preventDefault()
    setSaving(true)
    try {
      await commerceService.paySupplier({ ...payment, purchase_id: purchaseId })
      notify('Supplier payment recorded.')
      setShowPayment(false)
      setPayment({ amount: '', payment_method: 'cash', reference_number: '', notes: '' })
      setReload((current) => current + 1)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSaving(false)
    }
  }

  if (!purchase) return <div className="panel skeleton" style={{ minHeight: 260 }} />

  return (
    <div className="commerce-page">
      <div className="page-heading">
        <div><Link className="back-link" to="/purchases"><ArrowLeft size={14} />Purchases</Link><span className="eyebrow">PURCHASE DETAIL</span><h1>{purchase.invoice_number}</h1><p>{purchase.supplier_name} · {purchase.purchase_date}</p></div>
        {Number(purchase.outstanding_amount) > 0 && <button className="primary-button" onClick={() => setShowPayment(true)}><CreditCard size={15} />Pay supplier</button>}
      </div>
      <section className="kpi-grid commerce-kpis">
        <article className="kpi-card"><div className="kpi-copy"><span>Total</span><strong>{amount(purchase.total_amount)}</strong></div></article>
        <article className="kpi-card"><div className="kpi-copy"><span>Paid</span><strong>{amount(purchase.paid_amount)}</strong></div></article>
        <article className="kpi-card"><div className="kpi-copy"><span>Outstanding</span><strong>{amount(purchase.outstanding_amount)}</strong></div></article>
        <article className="kpi-card"><div className="kpi-copy"><span>Payment status</span><strong>{purchase.payment_status}</strong></div></article>
      </section>
      <section className="panel commerce-panel">
        <div className="panel-heading"><div><h2>Purchased products</h2><p>Stock received and the purchase cost for each line.</p></div></div>
        <div className="data-table"><table><thead><tr><th>Product</th><th>Quantity</th><th>Unit cost</th><th>Discount</th><th>Tax</th><th>Line total</th></tr></thead>
          <tbody>{purchase.items.map((item) => <tr key={item.id}><td><strong>{item.product_name}</strong></td><td>{item.quantity}</td><td>{amount(item.unit_cost)}</td><td>{amount(item.discount)}</td><td>{amount(item.tax)}</td><td>{amount(item.total)}</td></tr>)}</tbody>
        </table></div>
      </section>
      <section className="panel commerce-panel"><div className="panel-heading"><div><h2>Stock impact</h2><p>Inventory movements created by this purchase.</p></div></div>
        <div className="data-table"><table><thead><tr><th>Product</th><th>Received</th><th>Previous stock</th><th>New stock</th><th>Date</th></tr></thead>
          <tbody>{purchase.stock_movements?.length ? purchase.stock_movements.map((movement, index) => <tr key={`${movement.product_id}-${index}`}><td>{movement.product_name}</td><td>{movement.quantity}</td><td>{movement.previous_stock}</td><td>{movement.new_stock}</td><td>{new Date(movement.created_at).toLocaleString()}</td></tr>) : <tr><td colSpan="5" className="empty-cell">No stock movement recorded.</td></tr>}</tbody>
        </table></div>
      </section>
      <section className="panel commerce-panel"><div className="panel-heading"><div><h2>Payments</h2></div></div>
        <div className="data-table"><table><thead><tr><th>Date</th><th>Amount</th><th>Method</th><th>Reference</th></tr></thead>
          <tbody>{purchase.payments?.length ? purchase.payments.map((item) => <tr key={item.id}><td>{new Date(item.payment_date).toLocaleString()}</td><td>{amount(item.amount)}</td><td>{item.payment_method}</td><td>{item.reference_number || '—'}</td></tr>) : <tr><td colSpan="4" className="empty-cell">No supplier payments recorded.</td></tr>}</tbody>
        </table></div>
      </section>
      {showPayment && <div className="modal-backdrop" onClick={() => setShowPayment(false)}><div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header"><h3>Pay supplier</h3><button className="ghost-button" onClick={() => setShowPayment(false)}>Close</button></div>
        <form className="inventory-form" onSubmit={submitPayment}>
          <p>Purchase outstanding: <strong>{amount(purchase.outstanding_amount)}</strong></p>
          <label>Amount<input required type="number" min="0.01" max={purchase.outstanding_amount} step="0.01" value={payment.amount} onChange={(event) => setPayment({ ...payment, amount: event.target.value })} /></label>
          <label>Payment method<select value={payment.payment_method} onChange={(event) => setPayment({ ...payment, payment_method: event.target.value })}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="mobile_wallet">Mobile wallet</option><option value="other">Other</option></select></label>
          <label>Reference number<input value={payment.reference_number} onChange={(event) => setPayment({ ...payment, reference_number: event.target.value })} /></label>
          <label>Notes<textarea rows={2} value={payment.notes} onChange={(event) => setPayment({ ...payment, notes: event.target.value })} /></label>
          <div className="modal-actions"><button type="button" className="ghost-button" onClick={() => setShowPayment(false)}>Cancel</button><button className="primary-button" disabled={saving}>{saving ? 'Recording…' : 'Record payment'}</button></div>
        </form>
      </div></div>}
    </div>
  )
}
