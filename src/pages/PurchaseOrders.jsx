import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Check, Plus, Search, Truck } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { inventoryService } from '../services/inventoryService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const blank = () => ({ product_id: '', quantity: '1', expected_unit_cost: '' })

export default function PurchaseOrders() {
  const [orders, setOrders] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [open, setOpen] = useState(false)
  const [receiveOrder, setReceiveOrder] = useState(null)
  const [supplierId, setSupplierId] = useState('')
  const [delivery, setDelivery] = useState('')
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState([blank()])
  const [invoice, setInvoice] = useState('')
  const [paid, setPaid] = useState('0')
  const [busy, setBusy] = useState(false)
  const { notify } = useToast()
  const location = useLocation()

  const refresh = useCallback(async () => {
    const result = await commerceService.getPurchaseOrders({ page, limit: 10, search })
    setOrders(result.items || [])
    setTotal(result.total || 0)
  }, [page, search])

  useEffect(() => { refresh().catch((error) => notify(getApiErrorMessage(error), 'error')) }, [refresh, notify])
  useEffect(() => {
    Promise.all([inventoryService.getSuppliers(), inventoryService.getProducts({ limit: 200 })])
      .then(([s, p]) => { setSuppliers(s.filter((x) => x.is_active)); setProducts((p.items || []).filter((x) => x.is_active)) })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
  }, [notify])
  useEffect(() => {
    if (location.state?.restockProductId) {
      setLines([{ ...blank(), product_id: location.state.restockProductId, quantity: String(location.state.restockQuantity || 1) }])
      const preferred = suppliers.find((supplier) => supplier.name === location.state.supplierName)
      if (preferred) setSupplierId(preferred.id)
      setOpen(true)
      window.history.replaceState({}, document.title)
    }
  }, [location.state, suppliers])

  async function submitOrder(event) {
    event.preventDefault(); setBusy(true)
    try {
      await commerceService.createPurchaseOrder({ supplier_id: supplierId, expected_delivery_date: delivery || null, notes: notes || null, items: lines })
      notify('Supplier order created as a draft.')
      setOpen(false); setSupplierId(''); setDelivery(''); setNotes(''); setLines([blank()]); await refresh()
    } catch (error) { notify(getApiErrorMessage(error), 'error') } finally { setBusy(false) }
  }

  async function changeStatus(order, status) {
    try { await commerceService.updatePurchaseOrder(order.id, status); notify(status === 'ordered' ? 'Order marked as placed with supplier.' : 'Order cancelled.'); await refresh() }
    catch (error) { notify(getApiErrorMessage(error), 'error') }
  }

  async function receive(event) {
    event.preventDefault(); setBusy(true)
    try {
      const result = await commerceService.receivePurchaseOrder(receiveOrder.id, {
        supplier_id: receiveOrder.supplier_id, invoice_number: invoice,
        paid_amount: paid, items: receiveOrder.items.map((item) => ({ product_id: item.product_id, quantity: item.quantity, unit_cost: item.expected_unit_cost, discount: 0, tax: 0 })),
      })
      notify('Goods received. Purchase recorded and inventory updated.')
      setReceiveOrder(null); await refresh()
      if (result.purchase?.id) window.location.assign(`/purchases/${result.purchase.id}`)
    } catch (error) { notify(getApiErrorMessage(error), 'error') } finally { setBusy(false) }
  }

  return <div className="inventory-subpage">
    <section className="panel inventory-panel">
      <div className="panel-heading"><div><h2>Supplier purchase orders</h2><p>Create orders for suppliers, track placement, then receive stock into inventory.</p></div><button className="primary-button" onClick={() => setOpen(true)}><Plus size={16}/> New order</button></div>
      <div className="table-toolbar"><label className="search-input"><Search size={16}/><input aria-label="Search purchase orders" placeholder="Search order number" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }}/></label></div>
      <div className="data-table"><table><thead><tr><th>Order</th><th>Supplier</th><th>Items</th><th>Expected delivery</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        {!orders.length ? <tr><td className="empty-cell" colSpan="6">No supplier orders found. Create one to track upcoming stock.</td></tr> : orders.map((order) => <tr key={order.id}>
          <td><strong>{order.order_number}</strong><small className="table-secondary">{new Date(order.created_at).toLocaleDateString()}</small></td><td>{order.supplier_name}</td><td>{order.items.map((item) => `${item.product_name} × ${item.quantity}`).join(', ')}</td><td>{order.expected_delivery_date || '—'}</td><td><span className={`tag ${order.status === 'received' ? 'success' : order.status === 'cancelled' ? 'danger' : 'warning'}`}>{order.status}</span></td>
          <td className="table-actions">{order.status === 'draft' && <><button className="ghost-button small" onClick={() => changeStatus(order, 'ordered')}><Truck size={14}/> Mark ordered</button><button className="ghost-button small" onClick={() => changeStatus(order, 'cancelled')}>Cancel</button></>}{order.status === 'ordered' && <button className="primary-button small" onClick={() => { setReceiveOrder(order); setInvoice(''); setPaid('0') }}><Check size={14}/> Receive goods</button>}{order.purchase_id && <Link className="ghost-button small" to={`/purchases/${order.purchase_id}`}>View purchase</Link>}</td>
        </tr>)}
      </tbody></table></div>
      {total > 10 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((v) => v - 1)}>Previous</button><span>Page {page} of {Math.ceil(total / 10)}</span><button className="ghost-button" disabled={page >= Math.ceil(total / 10)} onClick={() => setPage((v) => v + 1)}>Next</button></div>}
    </section>
    {open && <div className="modal-backdrop" role="presentation"><form className="modal-card purchase-order-modal" onSubmit={submitOrder}><div className="panel-heading"><div><span className="eyebrow">SUPPLIER ORDER</span><h2>New purchase order</h2></div><button type="button" className="icon-button-inline" onClick={() => setOpen(false)}>×</button></div>
      <label>Supplier<select required value={supplierId} onChange={(e) => setSupplierId(e.target.value)}><option value="">Select supplier</option>{suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
      <div className="purchase-meta"><label>Expected delivery<input type="date" value={delivery} onChange={(e) => setDelivery(e.target.value)}/></label><label>Notes<input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional order notes"/></label></div>
      <div className="purchase-lines"><h3>Products</h3>{lines.map((line, index) => <div className="purchase-line order-line" key={index}><select required value={line.product_id} onChange={(e) => { const p = products.find((x) => x.id === e.target.value); setLines((xs) => xs.map((l, i) => i === index ? { ...l, product_id: e.target.value, expected_unit_cost: p?.cost_price || '' } : l)) }}><option value="">Select product</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}</select><input aria-label="Quantity" required type="number" min="0.01" step="0.01" value={line.quantity} onChange={(e) => setLines((xs) => xs.map((l, i) => i === index ? { ...l, quantity: e.target.value } : l))}/><input aria-label="Expected unit cost" required type="number" min="0" step="0.01" placeholder="Expected cost" value={line.expected_unit_cost} onChange={(e) => setLines((xs) => xs.map((l, i) => i === index ? { ...l, expected_unit_cost: e.target.value } : l))}/><button type="button" className="ghost-button small" disabled={lines.length === 1} onClick={() => setLines((xs) => xs.filter((_, i) => i !== index))}>Remove</button></div>)}<button type="button" className="ghost-button" onClick={() => setLines((xs) => [...xs, blank()])}><Plus size={14}/> Add product</button></div>
      <div className="modal-actions"><button type="button" className="ghost-button" onClick={() => setOpen(false)}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save draft order'}</button></div>
    </form></div>}
    {receiveOrder && <div className="modal-backdrop" role="presentation"><form className="modal-card" onSubmit={receive}><div className="panel-heading"><div><span className="eyebrow">RECEIVE STOCK</span><h2>{receiveOrder.order_number}</h2><p>Confirm supplier invoice and payment. Ordered quantities and costs will be recorded as a purchase.</p></div><button type="button" className="icon-button-inline" onClick={() => setReceiveOrder(null)}>×</button></div><label>Supplier invoice number<input required maxLength="80" value={invoice} onChange={(e) => setInvoice(e.target.value)}/></label><label>Amount paid<input type="number" min="0" step="0.01" value={paid} onChange={(e) => setPaid(e.target.value)}/></label><ul>{receiveOrder.items.map((item) => <li key={item.id}>{item.product_name} · {item.quantity} × {formatCurrency(item.expected_unit_cost)}</li>)}</ul><div className="modal-actions"><button type="button" className="ghost-button" onClick={() => setReceiveOrder(null)}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? 'Receiving…' : 'Receive and update stock'}</button></div></form></div>}
  </div>
}
