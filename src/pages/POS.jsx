import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Minus, Plus, Search, ShoppingCart, Trash2 } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { inventoryService } from '../services/inventoryService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const currency = formatCurrency

export default function POS() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [cart, setCart] = useState([])
  const [customerId, setCustomerId] = useState('')
  const [matchedCustomer, setMatchedCustomer] = useState(null)
  const [customerLookupLoading, setCustomerLookupLoading] = useState(false)
  const [newCustomer, setNewCustomer] = useState({ name: '', phone: '', email: '' })
  const [discount, setDiscount] = useState('0')
  const [tax, setTax] = useState('0')
  const [paid, setPaid] = useState('0')
  const [paymentMethod, setPaymentMethod] = useState('cash')
  const [loading, setLoading] = useState(true)
  const [checkingOut, setCheckingOut] = useState(false)
  const { notify } = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    let active = true
    inventoryService.getCategories().then((categoryList) => {
      if (active) {
        setCategories(categoryList)
      }
    }).catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [notify])

  useEffect(() => {
    const phone = newCustomer.phone.trim()
    const digits = phone.replace(/\D/g, '')
    if (digits.length < 7) {
      setCustomerLookupLoading(false)
      return undefined
    }
    let active = true
    const timer = window.setTimeout(async () => {
      setCustomerLookupLoading(true)
      try {
        const result = await commerceService.getCustomers({ search: phone, page: 1, limit: 50 })
        const match = (result.items || []).find((customer) => (
          customer.is_active && customer.phone?.replace(/\D/g, '') === digits
        ))
        if (active && match) {
          setCustomerId(match.id)
          setMatchedCustomer(match)
          setNewCustomer((current) => ({ ...current, name: match.name }))
        }
      } catch {
        // A lookup failure must not block a new sale; checkout will report any save error.
      } finally {
        if (active) setCustomerLookupLoading(false)
      }
    }, 350)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [newCustomer.phone])

  useEffect(() => {
    let active = true
    inventoryService.getProducts({ search: debouncedQuery, category_id: categoryId || undefined, active_only: true, limit: 100 })
      .then((data) => { if (active) setProducts((data.items || []).filter((product) => product.is_active)) })
      .catch((error) => { if (active) notify(getApiErrorMessage(error), 'error') })
    return () => { active = false }
  }, [debouncedQuery, categoryId, notify])

  const subtotal = useMemo(() => cart.reduce((sum, item) => sum + Number(item.product.selling_price) * item.quantity, 0), [cart])
  const lineDiscounts = useMemo(() => cart.reduce((sum, item) => sum + Number(item.discount || 0), 0), [cart])
  const lineTaxes = useMemo(() => cart.reduce((sum, item) => sum + Number(item.tax || 0), 0), [cart])
  const totalDiscount = Number(discount || 0) + lineDiscounts
  const totalTax = Number(tax || 0) + lineTaxes
  const total = Math.max(0, subtotal - totalDiscount + totalTax)

  function addProduct(product) {
    if (Number(product.current_stock) <= 0) {
      notify(`${product.name} is out of stock.`, 'error')
      return
    }
    const found = cart.find((item) => item.product.id === product.id)
    if (found && found.quantity + 1 > Number(product.current_stock)) {
      notify(`Only ${product.current_stock} units of ${product.name} are available.`, 'error')
      return
    }
    setCart((items) => found
      ? items.map((item) => item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item)
      : [...items, { product, quantity: 1, discount: '0', tax: '0' }])
  }

  function setQuantity(productId, next) {
    const product = cart.find((item) => item.product.id === productId)?.product
    if (!product) return
    if (next <= 0) {
      setCart((items) => items.filter((item) => item.product.id !== productId))
      return
    }
    if (next > Number(product.current_stock)) {
      notify(`Only ${product.current_stock} units of ${product.name} are available.`, 'error')
      return
    }
    setCart((items) => items.map((item) => item.product.id === productId ? { ...item, quantity: next } : item))
  }

  async function checkout(event) {
    event.preventDefault()
    if (cart.length === 0) {
      notify('Add at least one product to the cart.', 'error')
      return
    }
    setCheckingOut(true)
    try {
      const sale = await commerceService.createSale({
        customer_id: customerId || null,
        new_customer: customerId ? null : {
          name: newCustomer.name.trim(),
          phone: newCustomer.phone.trim() || null,
          email: newCustomer.email.trim() || null,
        },
        discount,
        tax,
        paid_amount: paid,
        payment_method: paymentMethod,
        items: cart.map(({ product, quantity, discount: lineDiscount, tax: lineTax }) => ({
          product_id: product.id,
          quantity,
          discount: lineDiscount,
          tax: lineTax,
        })),
      })
      notify(`Sale ${sale.invoice_number} completed.`)
      setCart([])
      setCustomerId('')
      setMatchedCustomer(null)
      setNewCustomer({ name: '', phone: '', email: '' })
      setDiscount('0')
      setTax('0')
      setPaid('0')
      navigate(`/sales/${sale.id}`)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setCheckingOut(false)
    }
  }

  if (loading) return <div className="panel skeleton" style={{ minHeight: 360 }} />
  return (
    <div className="commerce-page pos-page">
      <div className="page-heading"><div><span className="eyebrow">POINT OF SALE</span><h1>New sale</h1><p>Search by product name, SKU, or barcode and add items to the cart.</p></div></div>
      <div className="pos-layout">
        <section className="panel pos-catalog">
          <div className="pos-search-row"><div className="search-input"><Search size={15} /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search product, SKU, barcode…" /></div>
            <select className="filter-select" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select>
          </div>
          <div className="pos-product-grid">{products.length === 0 ? <div className="commerce-empty">No active products found. Add inventory before selling.</div> : products.map((product) => {
            const stock = Number(product.current_stock)
            return <button type="button" key={product.id} className="pos-product-card" disabled={stock <= 0} onClick={() => addProduct(product)}>
              <span className="pos-product-title">{product.name}</span><small>{product.sku}{product.barcode ? ` · ${product.barcode}` : ''}</small>
              <strong>{currency(product.selling_price)}</strong><span className={stock > 0 ? 'stock-available' : 'stock-empty'}>{stock > 0 ? `${product.current_stock} in stock` : 'Out of stock'}</span>
            </button>
          })}</div>
        </section>
        <form className="panel pos-cart" onSubmit={checkout}>
          <div className="pos-cart-heading"><div><h2><ShoppingCart size={17} />Cart</h2><span>{cart.reduce((sum, item) => sum + item.quantity, 0)} items</span></div><button type="button" className="ghost-button" disabled={!cart.length} onClick={() => setCart([])}>Clear</button></div>
          <div className="pos-cart-items">{cart.length === 0 ? <div className="commerce-empty">Select a product to begin a sale.</div> : cart.map(({ product, quantity, discount: lineDiscount, tax: lineTax }) => <div className="pos-cart-item" key={product.id}>
            <div className="pos-cart-product"><strong>{product.name}</strong><small>{currency(product.selling_price)} each · {product.current_stock} available</small>
              <div className="pos-line-adjustments">
                <label>Discount<input aria-label={`Discount for ${product.name}`} type="number" min="0" step="0.01" value={lineDiscount} onChange={(event) => setCart((items) => items.map((item) => item.product.id === product.id ? { ...item, discount: event.target.value } : item))} /></label>
                <label>Tax<input aria-label={`Tax for ${product.name}`} type="number" min="0" step="0.01" value={lineTax} onChange={(event) => setCart((items) => items.map((item) => item.product.id === product.id ? { ...item, tax: event.target.value } : item))} /></label>
              </div>
            </div>
            <div className="quantity-control"><button type="button" aria-label="Decrease quantity" onClick={() => setQuantity(product.id, quantity - 1)}><Minus size={13} /></button><input aria-label={`Quantity for ${product.name}`} type="number" min="0.01" max={product.current_stock} step="0.01" value={quantity} onChange={(event) => setQuantity(product.id, Number(event.target.value))} /><button type="button" aria-label="Increase quantity" onClick={() => setQuantity(product.id, quantity + 1)}><Plus size={13} /></button></div>
            <strong>{currency(Number(product.selling_price) * quantity - Number(lineDiscount || 0) + Number(lineTax || 0))}</strong><button type="button" className="icon-button-inline danger" aria-label={`Remove ${product.name}`} onClick={() => setQuantity(product.id, 0)}><Trash2 size={14} /></button>
          </div>)}</div>
          <div className="pos-checkout-fields">
            <div className="pos-new-customer-fields">
              <label>Customer name *<input required minLength="1" maxLength="160" autoComplete="name" value={newCustomer.name} readOnly={Boolean(matchedCustomer)} onChange={(event) => setNewCustomer({ ...newCustomer, name: event.target.value })} placeholder="Full name" /></label>
              <label>Phone number *<input required type="tel" inputMode="numeric" minLength="7" maxLength="11" autoComplete="tel" value={newCustomer.phone} onChange={(event) => { setCustomerId(''); setMatchedCustomer(null); setNewCustomer((current) => ({ ...current, name: matchedCustomer ? '' : current.name, phone: event.target.value })) }} placeholder="Enter up to 11 digits" />{customerLookupLoading && <small>Checking customer…</small>}</label>
              <label>Email (optional)<input type="email" maxLength="320" autoComplete="email" value={newCustomer.email} onChange={(event) => setNewCustomer({ ...newCustomer, email: event.target.value })} placeholder="Email address" /></label>
              {matchedCustomer && <p className="pos-customer-match">Returning customer found: <strong>{matchedCustomer.name}</strong>. This sale will be saved to their existing customer record.</p>}
            </div>
            <div className="pos-small-fields">
              <label>Order discount<input type="number" min="0" step="0.01" max={Math.max(0, subtotal - lineDiscounts)} value={discount} onChange={(event) => setDiscount(event.target.value)} /></label>
              <label>Tax<input type="number" min="0" step="0.01" value={tax} onChange={(event) => setTax(event.target.value)} /></label>
            </div>
            <div className="pos-small-fields">
              <label>Paid now<input type="number" min="0" step="0.01" max={total} value={paid} onChange={(event) => setPaid(event.target.value)} /></label>
              <label>Payment method<select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="mobile_wallet">Mobile wallet</option><option value="other">Other</option></select></label>
            </div>
          </div>
          <div className="pos-totals"><div><span>Subtotal</span><strong>{currency(subtotal)}</strong></div><div><span>Discount</span><strong>−{currency(totalDiscount)}</strong></div><div><span>Tax</span><strong>{currency(totalTax)}</strong></div><div className="pos-grand-total"><span>Total due</span><strong>{currency(total)}</strong></div><div><span>Balance due</span><strong>{currency(Math.max(0, total - Number(paid || 0)))}</strong></div></div>
          <button className="primary-button pos-checkout-button" disabled={checkingOut || cart.length === 0}>{checkingOut ? 'Processing…' : 'Complete sale'}</button>
        </form>
      </div>
    </div>
  )
}
