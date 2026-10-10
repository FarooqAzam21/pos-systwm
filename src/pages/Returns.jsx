import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RotateCcw, Search } from 'lucide-react'
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
  const [invoice, setInvoice] = useState('')
  const [sale, setSale] = useState(null)
  const [findingSale, setFindingSale] = useState(false)
  const [returnQuantities, setReturnQuantities] = useState({})
  const [returnMethod, setReturnMethod] = useState('cash')
  const [returnNotes, setReturnNotes] = useState('')
  const [submittingReturn, setSubmittingReturn] = useState(false)
  const [reload, setReload] = useState(0)
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
  }, [page, search, notify, reload])

  const pages = Math.max(1, Math.ceil(total / 20))

  async function findSale(event) {
    event.preventDefault()
    if (!invoice.trim()) return
    setFindingSale(true)
    setSale(null)
    setReturnQuantities({})
    try {
      const result = await commerceService.getSales({ search: invoice.trim(), page: 1, limit: 200 })
      const match = result.items.find((item) => item.invoice_number?.trim().toLowerCase() === invoice.trim().toLowerCase())
      if (!match) {
        notify('No sale found with that invoice number.', 'error')
        return
      }
      const detail = await commerceService.getSale(match.id)
      setSale(detail)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setFindingSale(false)
    }
  }

  async function submitReturn(event) {
    event.preventDefault()
    if (!sale) return
    const returnItems = Object.entries(returnQuantities)
      .filter(([, quantity]) => Number(quantity) > 0)
      .map(([sale_item_id, quantity]) => ({ sale_item_id, quantity: Number(quantity) }))
    if (!returnItems.length) {
      notify('Enter a return quantity for at least one product.', 'error')
      return
    }
    setSubmittingReturn(true)
    try {
      const result = await commerceService.returnSale(sale.id, {
        items: returnItems,
        payment_method: returnMethod,
        notes: returnNotes,
      })
      notify(`Return recorded. Refund: ${amount(result.refund_amount)}`)
      setSale(null)
      setInvoice('')
      setReturnQuantities({})
      setReturnNotes('')
      setReload((value) => value + 1)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSubmittingReturn(false)
    }
  }

  const returnableItems = sale?.items?.filter((item) => Number(item.returned_quantity) < Number(item.quantity)) || []
  const estimatedRefund = returnableItems.reduce((sum, item) => {
    const quantity = Number(returnQuantities[item.id] || 0)
    const unitNet = Number(item.line_total) / Number(item.quantity)
    return sum + unitNet * quantity
  }, 0)

  return (
    <div className="commerce-page">
      <div className="page-heading"><div><span className="eyebrow">TRANSACTIONS</span><h1>Returns</h1><p>Refunds and returned items recorded for this business.</p></div></div>
      <section className="panel commerce-panel return-create-panel">
        <div className="panel-heading"><div><h2>Record a return</h2><p>Find the original sale by invoice, then choose the products and quantities being returned.</p></div></div>
        <form className="return-lookup" onSubmit={findSale}>
          <label>Invoice number<input value={invoice} onChange={(event) => setInvoice(event.target.value)} placeholder="e.g. INV-20261008-5A2BC774" required /></label>
          <button className="primary-button" disabled={findingSale}><Search size={15} />{findingSale ? 'Searching…' : 'Find sale'}</button>
        </form>
        {sale && <form className="return-entry" onSubmit={submitReturn}>
          <div className="return-sale-summary"><div><span className="eyebrow">SALE FOUND</span><h3>{sale.invoice_number}</h3><p>{sale.customer_name || 'Walk-in customer'} · {new Date(sale.sale_date).toLocaleString()}</p></div><span className="status-pill">{sale.status?.replaceAll('_', ' ')}</span></div>
          {returnableItems.length ? <>
            <div className="data-table return-products-table"><table><thead><tr><th>Product</th><th>SKU</th><th>Sold</th><th>Already returned</th><th>Return quantity</th><th>Estimated refund</th></tr></thead><tbody>
              {returnableItems.map((item) => {
                const remaining = Number(item.quantity) - Number(item.returned_quantity)
                const quantity = Number(returnQuantities[item.id] || 0)
                return <tr key={item.id}><td><strong>{item.product_name}</strong></td><td>{item.sku || '—'}</td><td>{item.quantity}</td><td>{item.returned_quantity}</td><td><input className="return-quantity-input" aria-label={`Return quantity for ${item.product_name}`} type="number" min="0" max={remaining} step="0.01" value={returnQuantities[item.id] || ''} onChange={(event) => setReturnQuantities((current) => ({ ...current, [item.id]: event.target.value }))} placeholder={`Max ${remaining}`} /></td><td>{amount((Number(item.line_total) / Number(item.quantity)) * quantity)}</td></tr>
              })}
            </tbody></table></div>
            <div className="return-form-footer">
              <label>Refund method<select value={returnMethod} onChange={(event) => setReturnMethod(event.target.value)}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="mobile_wallet">Mobile wallet</option><option value="other">Other</option></select></label>
              <label>Reason / notes<input value={returnNotes} onChange={(event) => setReturnNotes(event.target.value)} maxLength="500" placeholder="Optional return details" /></label>
              <div className="return-refund-total"><span>Estimated refund</span><strong>{amount(estimatedRefund)}</strong><small>Final amount is calculated from the original sale, including its discounts and tax.</small></div>
              <button className="primary-button" disabled={submittingReturn || estimatedRefund <= 0}><RotateCcw size={15} />{submittingReturn ? 'Processing…' : 'Confirm return'}</button>
            </div>
          </> : <p className="return-no-items">This sale has no remaining returnable items.</p>}
        </form>}
      </section>
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
