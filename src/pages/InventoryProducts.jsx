import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Eye, PencilLine, Plus, Search, Trash2 } from 'lucide-react'
import { inventoryService } from '../services/inventoryService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const emptyForm = {
  category_id: '',
  sku: '',
  barcode: '',
  name: '',
  description: '',
  brand: '',
  unit: 'pcs',
  cost_price: '',
  selling_price: '',
  opening_stock: '0',
  minimum_stock: '0',
  maximum_stock: '',
  is_active: true,
}

const stockOptions = ['ALL', 'LOW_STOCK', 'OUT_OF_STOCK', 'IN_STOCK']

export default function InventoryProducts() {
  const { notify } = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [categories, setCategories] = useState([])
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [page, setPage] = useState(1)
  const [limit] = useState(10)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [categoryText, setCategoryText] = useState('')
  const [creatingCategory, setCreatingCategory] = useState(false)

  const fetchData = async () => {
    const [categoryList, productList] = await Promise.all([
      inventoryService.getCategories(),
      inventoryService.getProducts({
        search,
        category_id: categoryFilter === 'all' ? undefined : categoryFilter,
        low_stock: statusFilter === 'LOW_STOCK',
        out_of_stock: statusFilter === 'OUT_OF_STOCK',
        page,
        limit,
      }),
    ])
    setCategories(categoryList)
    setItems(productList.items || [])
    setTotal(productList.total || 0)
    setLoading(false)
  }

  useEffect(() => {
    setLoading(true)
    fetchData().catch((error) => {
      setLoading(false)
      notify(getApiErrorMessage(error), 'error')
    })
  }, [search, categoryFilter, statusFilter, page, notify])

  const pageCount = Math.max(1, Math.ceil(total / limit))

  function openCreate() {
    setEditingId(null)
    setForm(emptyForm)
    setFormError('')
    setCategoryText('')
    setShowForm(true)
  }

  function openEdit(item) {
    setEditingId(item.id)
    setFormError('')
    setCategoryText(item.category_name || '')
    setForm({
      category_id: item.category_id || '',
      sku: item.sku,
      barcode: item.barcode || '',
      name: item.name,
      description: item.description || '',
      brand: item.brand || '',
      unit: item.unit || 'pcs',
      cost_price: item.cost_price,
      selling_price: item.selling_price,
      opening_stock: item.current_stock,
      minimum_stock: item.minimum_stock,
      maximum_stock: item.maximum_stock || '',
      is_active: item.is_active,
    })
    setShowForm(true)
  }

  function updateCategoryText(value) {
    setCategoryText(value)
    const matching = categories.find((category) => category.name.trim().toLocaleLowerCase() === value.trim().toLocaleLowerCase())
    setForm((current) => ({ ...current, category_id: matching?.id || '' }))
  }

  async function addCategory() {
    const name = categoryText.trim()
    if (!name) return
    const matching = categories.find((category) => category.name.trim().toLocaleLowerCase() === name.toLocaleLowerCase())
    if (matching) {
      setForm((current) => ({ ...current, category_id: matching.id }))
      setCategoryText(matching.name)
      return
    }
    setCreatingCategory(true)
    try {
      const category = await inventoryService.createCategory({ name, description: '', is_active: true })
      setCategories((current) => [...current, category])
      setForm((current) => ({ ...current, category_id: category.id }))
      setCategoryText(category.name)
      notify(`Category “${category.name}” added.`)
    } catch (error) {
      const message = getApiErrorMessage(error)
      setFormError(message)
      notify(message, 'error')
    } finally {
      setCreatingCategory(false)
    }
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...form,
        category_id: form.category_id || null,
        barcode: form.barcode || null,
        description: form.description || null,
        brand: form.brand || null,
        maximum_stock: form.maximum_stock === '' ? null : form.maximum_stock,
        opening_stock: form.opening_stock,
      }
      if (editingId) {
        delete payload.opening_stock
        await inventoryService.updateProduct(editingId, payload)
      } else {
        await inventoryService.createProduct(payload)
      }
      setShowForm(false)
      setForm(emptyForm)
      await fetchData()
      notify(editingId ? 'Product updated.' : 'Product added to inventory.')
    } catch (error) {
      const message = getApiErrorMessage(error)
      setFormError(message)
      notify(message, 'error')
    } finally {
      setSaving(false)
    }
  }

  async function deactivate(item) {
    try {
      await inventoryService.updateProduct(item.id, { ...item, is_active: false })
      await fetchData()
      notify('Product deactivated.')
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    }
  }

  useEffect(() => {
    if (location.state?.openAddProduct) {
      openCreate()
      navigate(location.pathname, { replace: true, state: null })
    }
  }, [location.key])

  if (loading) return <div className="panel skeleton" style={{ minHeight: 240 }} />

  return (
    <div className="inventory-subpage">
      <div className="subpage-toolbar">
        <div className="search-input">
          <Search size={15} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search products" aria-label="Search products" />
        </div>
        <select className="filter-select" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
          <option value="all">All categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>{category.name}</option>
          ))}
        </select>
        <select className="filter-select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          {stockOptions.map((option) => (<option key={option} value={option}>{option === 'ALL' ? 'All stock status' : option}</option>))}
        </select>
        <button className="primary-button" onClick={openCreate}><Plus size={14} />Add product</button>
      </div>

      {showForm && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)}>
          <div className="modal-card large product-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingId ? 'Edit product' : 'Add product'}</h3>
              <button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Close</button>
            </div>
            <form className="inventory-form two-column product-form" onSubmit={submit}>
              <p className="form-help span-2">Fields marked * are required. SKU must be unique in this business.</p>
              <label>
                Product name *
                <input required minLength="1" maxLength="180" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="e.g. Arabica Coffee Beans" />
              </label>
              <label>
                SKU *
                <input required minLength="1" maxLength="80" value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} placeholder="e.g. COF-ARAB-001" />
              </label>
              <label>
                Barcode
                <input maxLength="80" value={form.barcode} onChange={(event) => setForm({ ...form, barcode: event.target.value })} placeholder="Optional UPC/EAN barcode" />
              </label>
              <label>
                Category
                <div className="product-category-field">
                  <input list="inventory-category-options" value={categoryText} onChange={(event) => updateCategoryText(event.target.value)} placeholder="Choose or type a category" />
                  <datalist id="inventory-category-options">
                    {categories.map((category) => <option key={category.id} value={category.name} />)}
                  </datalist>
                  {categoryText.trim() && !categories.some((category) => category.name.trim().toLocaleLowerCase() === categoryText.trim().toLocaleLowerCase()) && (
                    <button type="button" className="secondary-button category-add-button" onClick={addCategory} disabled={creatingCategory}>
                      <Plus size={14} />{creatingCategory ? 'Adding' : 'Add'}
                    </button>
                  )}
                </div>
              </label>
              <label>
                Brand
                <input maxLength="120" value={form.brand} onChange={(event) => setForm({ ...form, brand: event.target.value })} placeholder="Optional brand or manufacturer" />
              </label>
              <label>
                Unit of measure *
                <input required minLength="1" maxLength="40" value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} placeholder="pcs, kg, litre, box" />
              </label>
              <label>
                Cost price *
                <input required type="number" min="0" max="9999999999.99" step="0.01" value={form.cost_price} onChange={(event) => setForm({ ...form, cost_price: event.target.value })} placeholder="0.00" />
              </label>
              <label>
                Selling price *
                <input required type="number" min="0" max="9999999999.99" step="0.01" value={form.selling_price} onChange={(event) => setForm({ ...form, selling_price: event.target.value })} placeholder="0.00" />
              </label>
              <label>
                {editingId ? 'Current stock' : 'Opening stock *'}
                <input required={!editingId} readOnly={Boolean(editingId)} type="number" min="0" step="0.01" value={form.opening_stock} onChange={(event) => setForm({ ...form, opening_stock: event.target.value })} />
                {editingId && <small className="field-help">Use Inventory → Adjust stock to change stock quantities.</small>}
              </label>
              <label>
                Minimum stock
                <input type="number" min="0" step="0.01" value={form.minimum_stock} onChange={(event) => setForm({ ...form, minimum_stock: event.target.value })} />
              </label>
              <label>
                Maximum stock
                <input type="number" min="0" step="0.01" value={form.maximum_stock} onChange={(event) => setForm({ ...form, maximum_stock: event.target.value })} />
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
                Active
              </label>
              <label className="span-2">
                Description
                <textarea rows={3} maxLength="1000" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Optional product details" />
              </label>
              {formError && <div className="report-error span-2" role="alert">{formError}</div>}
              <div className="modal-actions span-2">
                <button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Saving…' : editingId ? 'Save changes' : 'Create product'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <section className="panel inventory-panel">
        <div className="panel-heading">
          <div>
            <h2>Products</h2>
            <p>Track pricing, stock levels, and inventory value.</p>
          </div>
        </div>

        <div className="data-table">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Category</th>
                <th>Cost</th>
                <th>Selling Price</th>
                <th>Stock</th>
                <th>Inventory Value</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan="9" className="empty-cell">No products found.</td></tr>
              ) : items.map((item) => (
                <tr key={item.id}>
                  <td><div className="product-name-cell"><strong>{item.name}</strong>{item.brand && <small>{item.brand}</small>}</div></td>
                  <td><span className="sku-chip">{item.sku}</span></td>
                  <td>{item.category_name || '—'}</td>
                  <td className="numeric-cell">{formatCurrency(item.cost_price)}</td>
                  <td className="numeric-cell">{formatCurrency(item.selling_price)}</td>
                  <td className="numeric-cell"><strong>{Number(item.current_stock || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong><small className="table-subtext">{item.unit}</small></td>
                  <td className="numeric-cell">{formatCurrency(item.inventory_value)}</td>
                  <td><span className={`stock-state ${item.stock_status === 'LOW_STOCK' ? 'warning' : item.stock_status === 'OUT_OF_STOCK' ? 'danger' : 'success'}`}>{item.stock_status === 'LOW_STOCK' ? 'Low stock' : item.stock_status === 'OUT_OF_STOCK' ? 'Out of stock' : 'In stock'}</span></td>
                  <td>
                    <div className="row-actions">
                      <button className="icon-button-inline" type="button" aria-label={`Edit ${item.name}`} title="Edit product" onClick={() => openEdit(item)}><PencilLine size={14} /></button>
                      <button className="icon-button-inline" type="button" aria-label={`View ${item.name}`} title="View details"><Eye size={14} /></button>
                      <button className="icon-button-inline danger" type="button" aria-label={`Deactivate ${item.name}`} title="Deactivate product" onClick={() => deactivate(item)}><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {total > limit && (
          <div className="pagination-row">
            <button className="ghost-button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button>
            <span>Page {page} of {pageCount}</span>
            <button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((current) => Math.min(pageCount, current + 1))}>Next</button>
          </div>
        )}
      </section>
    </div>
  )
}
