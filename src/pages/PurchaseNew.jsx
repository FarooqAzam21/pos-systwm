import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { inventoryService } from '../services/inventoryService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const blankLine = () => ({ product_id: '', quantity: '1', unit_cost: '', discount: '0', tax: '0' })
const money = formatCurrency

export default function PurchaseNew() {
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState([])
  const [supplierId, setSupplierId] = useState('')
  const [invoice, setInvoice] = useState('')
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10))
  const [lines, setLines] = useState([blankLine()])
  const [discount, setDiscount] = useState('0')
  const [tax, setTax] = useState('0')
  const [paid, setPaid] = useState('0')
  const [paymentMethod, setPaymentMethod] = useState('cash')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { notify } = useToast()

  useEffect(() => {
    let active = true
    Promise.all([
      inventoryService.getSuppliers(),
      inventoryService.getProducts({ limit: 200, page: 1, active_only: true }),
    ])
      .then(async ([supplierList, firstPage]) => {
        const totalPages = Math.ceil((firstPage.total || firstPage.items?.length || 0) / 200)
        const productPages = [firstPage]
        for (let page = 2; page <= totalPages; page += 4) {
          const batch = Array.from(
            { length: Math.min(4, totalPages - page + 1) },
            (_, index) => inventoryService.getProducts({ limit: 200, page: page + index, active_only: true }),
          )
          productPages.push(...await Promise.all(batch))
        }
        const productList = productPages.flatMap((page) => page.items || [])
        if (active) {
          setSuppliers(supplierList.filter((item) => item.is_active))
          setProducts(productList.filter((item) => item.is_active))
        }
      })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [notify])

  const subtotal = useMemo(() => lines.reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_cost || 0), 0), [lines])
  const total = Math.max(0, subtotal - lines.reduce((sum, line) => sum + Number(line.discount || 0), 0) - Number(discount || 0) + lines.reduce((sum, line) => sum + Number(line.tax || 0), 0) + Number(tax || 0))

  function updateLine(index, changes) {
    setLines((current) => current.map((line, lineIndex) => lineIndex === index ? { ...line, ...changes } : line))
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      const created = await commerceService.createPurchase({
        supplier_id: supplierId,
        invoice_number: invoice,
        purchase_date: purchaseDate,
        discount,
        tax,
        paid_amount: paid,
        payment_method: paymentMethod,
        items: lines.map((line) => ({
          product_id: line.product_id,
          quantity: line.quantity,
          unit_cost: line.unit_cost,
          discount: line.discount,
          tax: line.tax,
        })),
      })
      notify('Purchase recorded and inventory updated.')
      navigate('/purchases', { replace: true, state: { createdId: created.id } })
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="panel skeleton" style={{ minHeight: 280 }} />
  return (
    <div className="commerce-page">
      <div className="page-heading"><div><button className="back-link" onClick={() => navigate('/purchases')}><ArrowLeft size={14} />Purchases</button><span className="eyebrow">INBOUND STOCK</span><h1>New purchase</h1><p>Received products update stock and weighted average cost together.</p></div></div>
      <form className="panel purchase-form" onSubmit={submit}>
        <div className="purchase-meta">
          <label>Supplier<select required value={supplierId} onChange={(event) => setSupplierId(event.target.value)}><option value="">Select supplier</option>{suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}{supplier.company_name ? ` — ${supplier.company_name}` : ''}</option>)}</select></label>
          <label>Invoice number<input required maxLength="80" value={invoice} onChange={(event) => setInvoice(event.target.value)} /></label>
          <label>Purchase date<input required type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} /></label>
        </div>
        <div className="purchase-lines">
          <div className="purchase-line purchase-line-head"><span>Product</span><span>Quantity</span><span>Unit cost</span><span>Discount</span><span>Tax</span><span /></div>
          {lines.map((line, index) => <div className="purchase-line" key={index}>
            <select required value={line.product_id} onChange={(event) => {
              const product = products.find((item) => item.id === event.target.value)
              updateLine(index, { product_id: event.target.value, unit_cost: product?.cost_price || '' })
            }}><option value="">Select product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name} ({product.sku})</option>)}</select>
            <input aria-label="Quantity" required type="number" min="0.01" step="0.01" value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} />
            <input aria-label="Unit cost" required type="number" min="0" step="0.01" value={line.unit_cost} onChange={(event) => updateLine(index, { unit_cost: event.target.value })} />
            <input aria-label="Line discount" type="number" min="0" step="0.01" value={line.discount} onChange={(event) => updateLine(index, { discount: event.target.value })} />
            <input aria-label="Line tax" type="number" min="0" step="0.01" value={line.tax} onChange={(event) => updateLine(index, { tax: event.target.value })} />
            <button type="button" className="icon-button-inline danger" aria-label="Remove line" disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))}><Trash2 size={15} /></button>
          </div>)}
          <button type="button" className="ghost-button" onClick={() => setLines((current) => [...current, blankLine()])}><Plus size={14} />Add line</button>
        </div>
        <div className="purchase-footer">
          <div className="purchase-controls">
            <label>Purchase discount<input type="number" min="0" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} /></label>
            <label>Purchase tax<input type="number" min="0" step="0.01" value={tax} onChange={(event) => setTax(event.target.value)} /></label>
            <label>Amount paid<input type="number" min="0" step="0.01" max={total} value={paid} onChange={(event) => setPaid(event.target.value)} /></label>
            <label>Payment method<select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="mobile_wallet">Mobile wallet</option><option value="other">Other</option></select></label>
          </div>
          <div className="purchase-totals"><div><span>Subtotal</span><strong>{money(subtotal)}</strong></div><div><span>Total</span><strong>{money(total)}</strong></div><div><span>Outstanding</span><strong>{money(Math.max(0, total - Number(paid || 0)))}</strong></div></div>
        </div>
        <div className="modal-actions"><button type="button" className="ghost-button" onClick={() => navigate('/purchases')}>Cancel</button><button className="primary-button" disabled={saving || suppliers.length === 0 || products.length === 0}>{saving ? 'Saving…' : 'Save purchase'}</button></div>
      </form>
    </div>
  )
}
