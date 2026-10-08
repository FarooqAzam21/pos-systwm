import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Printer, RotateCcw } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { businessService } from '../services/businessService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { useAuth } from '../context/useAuth'
import { formatCurrency } from '../utils/formatters'

const amount = formatCurrency

export default function SaleDetails() {
  const { saleId } = useParams()
  const { user } = useAuth()
  const canManageReturns = ['Owner', 'Admin', 'Manager'].includes(user?.role)
  const { notify } = useToast()
  const [sale, setSale] = useState(null)
  const [business, setBusiness] = useState(null)
  const [reload, setReload] = useState(0)
  const [showReturn, setShowReturn] = useState(false)
  const [returnLines, setReturnLines] = useState({})
  const [returnNotes, setReturnNotes] = useState('')
  const [returnMethod, setReturnMethod] = useState('cash')
  const [returning, setReturning] = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([commerceService.getSale(saleId), businessService.get()])
      .then(([saleData, businessData]) => {
        if (active) { setSale(saleData); setBusiness(businessData) }
      })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
    return () => { active = false }
  }, [saleId, reload, notify])

  async function submitReturn(event) {
    event.preventDefault()
    const items = Object.entries(returnLines).filter(([, quantity]) => Number(quantity) > 0).map(([sale_item_id, quantity]) => ({ sale_item_id, quantity }))
    if (items.length === 0) {
      notify('Enter a return quantity for at least one product.', 'error')
      return
    }
    setReturning(true)
    try {
      await commerceService.returnSale(saleId, { items, notes: returnNotes, payment_method: returnMethod })
      notify('Return processed and stock restored.')
      setShowReturn(false)
      setReturnLines({})
      setReload((value) => value + 1)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setReturning(false)
    }
  }

  async function downloadInvoice() {
    setDownloading(true)
    try {
      const blob = await commerceService.downloadInvoicePdf(saleId)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${sale.invoice_number}.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setDownloading(false)
    }
  }

  if (!sale) return <div className="panel skeleton" style={{ minHeight: 240 }} />
  return (
    <div className="commerce-page invoice-page">
      <div className="page-heading sale-actions"><div><Link className="back-link" to="/sales"><ArrowLeft size={14} />Sales</Link><span className="eyebrow">SALE INVOICE</span><h1>{sale.invoice_number}</h1><p>{new Date(sale.sale_date).toLocaleString()} · {sale.status}</p></div>
        <div className="sale-action-buttons"><button className="ghost-button" onClick={() => window.print()}><Printer size={15} />Print invoice</button><button className="ghost-button" disabled={downloading} onClick={downloadInvoice}><Download size={15} />{downloading ? 'Preparing PDF…' : 'Download PDF'}</button>{canManageReturns && sale.status !== 'returned' && sale.status !== 'voided' && <button className="primary-button" onClick={() => setShowReturn(true)}><RotateCcw size={15} />Return items</button>}</div>
      </div>
      <article className="panel print-invoice invoice-card">
        <div className="invoice-heading"><div><span className="eyebrow">INVOICE</span><h2>{business?.business_name || user?.business_name}</h2><p>{business?.address || ''}{business?.phone ? ` · ${business.phone}` : ''}</p><p>{business?.email || ''}</p></div><div><strong>{sale.invoice_number}</strong><span>{new Date(sale.sale_date).toLocaleString()}</span><span>Cashier: {sale.cashier_name || user?.name}</span></div></div>
        <div className="invoice-customer"><span>Customer</span><strong>{sale.customer_name || 'Walk-in customer'}</strong>{sale.customer_phone && <span>{sale.customer_phone}</span>}{sale.customer_address && <span>{sale.customer_address}</span>}{sale.customer_id && <Link to={`/customers/${sale.customer_id}`}>View account</Link>}</div>
        <div className="data-table invoice-items"><table><thead><tr><th>Product</th><th>SKU</th><th>Qty</th><th>Unit price</th><th>Discount</th><th>Tax</th><th>Line total</th></tr></thead><tbody>
          {sale.items.map((item) => <tr key={item.id}><td>{item.product_name}{Number(item.returned_quantity) > 0 && <small className="returned-note">Returned {item.returned_quantity}</small>}</td><td>{item.sku}</td><td>{item.quantity}</td><td>{amount(item.unit_price)}</td><td>{amount(item.discount)}</td><td>{amount(item.tax)}</td><td>{amount(item.line_total)}</td></tr>)}
        </tbody></table></div>
        <div className="invoice-bottom">
          <div><h3>Payments</h3>{sale.payments?.length ? sale.payments.map((payment) => <p key={payment.id}>{new Date(payment.payment_date).toLocaleString()} · {payment.payment_method} · {amount(payment.amount)}</p>) : <p>No payments recorded.</p>}<p>Sale status: <strong>{sale.status}</strong></p></div>
          <dl className="invoice-totals"><div><dt>Subtotal</dt><dd>{amount(sale.subtotal)}</dd></div><div><dt>Discount</dt><dd>{amount(sale.discount)}</dd></div><div><dt>Tax</dt><dd>{amount(sale.tax)}</dd></div><div className="invoice-total"><dt>Total (net of returns)</dt><dd>{amount(sale.total_amount)}</dd></div><div><dt>Paid</dt><dd>{amount(sale.paid_amount)}</dd></div><div><dt>Outstanding</dt><dd>{amount(sale.outstanding_amount)}</dd></div>{user?.role !== 'Cashier' && <><div><dt>COGS</dt><dd>{amount(sale.cogs_amount)}</dd></div><div><dt>Gross profit</dt><dd>{amount(sale.gross_profit)}</dd></div></>}</dl>
        </div>
      </article>
      {!!sale.returns?.length && <section className="panel commerce-panel"><div className="panel-heading"><div><h2>Returns</h2></div></div><div className="data-table"><table><thead><tr><th>Date</th><th>Refund</th><th>Notes</th></tr></thead><tbody>{sale.returns.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td>{amount(item.refund_amount)}</td><td>{item.notes || '—'}</td></tr>)}</tbody></table></div></section>}
      {canManageReturns && showReturn && <div className="modal-backdrop" onClick={() => setShowReturn(false)}><div className="modal-card large" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header"><h3>Return sale items</h3><button className="ghost-button" onClick={() => setShowReturn(false)}>Close</button></div>
        <form className="inventory-form" onSubmit={submitReturn}>
          <div className="return-item-list">{sale.items.filter((item) => Number(item.returned_quantity) < Number(item.quantity)).map((item) => <label key={item.id}>{item.product_name} · remaining {Number(item.quantity) - Number(item.returned_quantity)}<input type="number" min="0" max={Number(item.quantity) - Number(item.returned_quantity)} step="0.01" value={returnLines[item.id] || ''} onChange={(event) => setReturnLines({ ...returnLines, [item.id]: event.target.value })} /></label>)}</div>
          <label>Refund method<select value={returnMethod} onChange={(event) => setReturnMethod(event.target.value)}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="mobile_wallet">Mobile wallet</option><option value="other">Other</option></select></label>
          <label>Notes<textarea rows={2} value={returnNotes} onChange={(event) => setReturnNotes(event.target.value)} /></label>
          <div className="modal-actions"><button type="button" className="ghost-button" onClick={() => setShowReturn(false)}>Cancel</button><button className="primary-button" disabled={returning}>{returning ? 'Processing…' : 'Confirm return'}</button></div>
        </form>
      </div></div>}
    </div>
  )
}
