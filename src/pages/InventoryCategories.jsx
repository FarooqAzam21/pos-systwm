import { useEffect, useMemo, useState } from 'react'
import { PencilLine, Plus, PowerOff, Search, Trash2 } from 'lucide-react'
import { inventoryService } from '../services/inventoryService'

const emptyForm = { name: '', description: '', is_active: true }

export default function InventoryCategories() {
  const [items, setItems] = useState([])
  const [products, setProducts] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 10
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [showForm, setShowForm] = useState(false)

  const fetchData = async () => {
    const [categories, productList] = await Promise.all([
      inventoryService.getCategories(),
      inventoryService.getProducts({ limit: 500 }),
    ])
    setItems(categories)
    setProducts(productList.items || [])
    setLoading(false)
  }

  useEffect(() => {
    fetchData().catch(() => setLoading(false))
  }, [])

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase()
    return items.filter((item) => !query || `${item.name} ${item.description || ''}`.toLowerCase().includes(query))
  }, [items, search])
  const pageCount = Math.max(1, Math.ceil(filteredItems.length / pageSize))
  const pageItems = filteredItems.slice((page - 1) * pageSize, page * pageSize)

  const productCountMap = useMemo(() => {
    const map = {}
    for (const product of products) {
      map[product.category_id] = (map[product.category_id] || 0) + 1
    }
    return map
  }, [products])

  function openCreate() {
    setEditingId(null)
    setForm(emptyForm)
    setShowForm(true)
  }

  function openEdit(item) {
    setEditingId(item.id)
    setForm({ name: item.name, description: item.description || '', is_active: item.is_active })
    setShowForm(true)
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        await inventoryService.updateCategory(editingId, form)
      } else {
        await inventoryService.createCategory(form)
      }
      setShowForm(false)
      setForm(emptyForm)
      await fetchData()
    } finally {
      setSaving(false)
    }
  }

  async function toggleStatus(item) {
    await inventoryService.updateCategory(item.id, { ...item, is_active: !item.is_active })
    await fetchData()
  }

  if (loading) return <div className="panel skeleton" style={{ minHeight: 220 }} />

  return (
    <div className="inventory-subpage">
      <div className="subpage-toolbar">
        <div className="search-input">
          <Search size={15} />
          <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search categories" aria-label="Search categories" />
        </div>
        <button className="primary-button" onClick={openCreate}><Plus size={14} />Add category</button>
      </div>

      {showForm && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingId ? 'Edit category' : 'Add category'}</h3>
              <button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Close</button>
            </div>
            <form className="inventory-form" onSubmit={submit}>
              <label>
                Category name
                <input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
              </label>
              <label>
                Description
                <textarea rows={4} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
                Active
              </label>
              <div className="modal-actions">
                <button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Saving…' : editingId ? 'Save changes' : 'Create category'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <section className="panel inventory-panel">
        <div className="panel-heading">
          <div>
            <h2>Categories</h2>
            <p>Organize products into logical groups.</p>
          </div>
        </div>

        <div className="data-table">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Description</th>
                <th>Product Count</th>
                <th>Status</th>
                <th>Created Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr><td colSpan="6" className="empty-cell">No categories found.</td></tr>
              ) : pageItems.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.name}</strong></td>
                  <td>{item.description || '—'}</td>
                  <td>{productCountMap[item.id] || 0}</td>
                  <td><span className={`tag ${item.is_active ? 'success' : 'muted'}`}>{item.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td>{new Date(item.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="row-actions">
                      <button className="icon-button-inline" onClick={() => openEdit(item)}><PencilLine size={14} /></button>
                      <button className="icon-button-inline danger" onClick={() => toggleStatus(item)}><PowerOff size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredItems.length > pageSize && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount} · {filteredItems.length} categories</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
