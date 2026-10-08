import { useEffect, useMemo, useState } from 'react'
import { Mail, PencilLine, Phone, Plus, Search, Trash2 } from 'lucide-react'
import { inventoryService } from '../services/inventoryService'
import { formatCurrency } from '../utils/formatters'

const emptyForm = {
  name: '',
  company_name: '',
  email: '',
  phone: '',
  address: '',
  tax_number: '',
  notes: '',
  is_active: true,
}

export default function InventorySuppliers() {
  const [items, setItems] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 10
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(emptyForm)

  const fetchData = async () => {
    const data = await inventoryService.getSuppliers()
    setItems(data)
    setLoading(false)
  }

  useEffect(() => {
    fetchData().catch(() => setLoading(false))
  }, [])

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase()
    return items.filter((item) => !query || `${item.name} ${item.company_name || ''} ${item.email || ''} ${item.phone || ''}`.toLowerCase().includes(query))
  }, [items, search])
  const pageCount = Math.max(1, Math.ceil(filteredItems.length / pageSize))
  const pageItems = filteredItems.slice((page - 1) * pageSize, page * pageSize)

  function openCreate() {
    setEditingId(null)
    setForm(emptyForm)
    setShowForm(true)
  }

  function openEdit(item) {
    setEditingId(item.id)
    setForm({
      name: item.name,
      company_name: item.company_name || '',
      email: item.email || '',
      phone: item.phone || '',
      address: item.address || '',
      tax_number: item.tax_number || '',
      notes: item.notes || '',
      is_active: item.is_active,
    })
    setShowForm(true)
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        await inventoryService.updateSupplier(editingId, form)
      } else {
        await inventoryService.createSupplier(form)
      }
      setShowForm(false)
      setForm(emptyForm)
      await fetchData()
    } finally {
      setSaving(false)
    }
  }

  async function toggleStatus(item) {
    await inventoryService.updateSupplier(item.id, { ...item, is_active: !item.is_active })
    await fetchData()
  }

  if (loading) return <div className="panel skeleton" style={{ minHeight: 220 }} />

  return (
    <div className="inventory-subpage">
      <div className="subpage-toolbar">
        <div className="search-input">
          <Search size={15} />
          <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search suppliers" aria-label="Search suppliers" />
        </div>
        <button className="primary-button" onClick={openCreate}><Plus size={14} />Add supplier</button>
      </div>

      {showForm && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)}>
          <div className="modal-card large" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingId ? 'Edit supplier' : 'Add supplier'}</h3>
              <button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Close</button>
            </div>
            <form className="inventory-form two-column" onSubmit={submit}>
              <label>
                Supplier name
                <input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
              </label>
              <label>
                Company name
                <input value={form.company_name} onChange={(event) => setForm({ ...form, company_name: event.target.value })} />
              </label>
              <label>
                Phone
                <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
              </label>
              <label>
                Email
                <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
              </label>
              <label className="span-2">
                Address
                <input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
              </label>
              <label>
                Tax number
                <input value={form.tax_number} onChange={(event) => setForm({ ...form, tax_number: event.target.value })} />
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
                Active
              </label>
              <label className="span-2">
                Notes
                <textarea rows={3} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
              </label>
              <div className="modal-actions span-2">
                <button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Saving…' : editingId ? 'Save changes' : 'Create supplier'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <section className="panel inventory-panel">
        <div className="panel-heading">
          <div>
            <h2>Suppliers</h2>
            <p>Keep supplier contact details and account status organized.</p>
          </div>
        </div>

        <div className="data-table">
          <table>
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Company</th>
                <th>Phone</th>
                <th>Email</th>
                <th>Outstanding</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr><td colSpan="7" className="empty-cell">No suppliers found.</td></tr>
              ) : pageItems.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.name}</strong></td>
                  <td>{item.company_name || '—'}</td>
                  <td>{item.phone || '—'}</td>
                  <td>{item.email || '—'}</td>
                  <td>{formatCurrency(item.outstanding_balance)}</td>
                  <td><span className={`tag ${item.is_active ? 'success' : 'muted'}`}>{item.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td>
                    <div className="row-actions">
                      <button className="icon-button-inline" onClick={() => openEdit(item)}><PencilLine size={14} /></button>
                      <button className="icon-button-inline danger" onClick={() => toggleStatus(item)}><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredItems.length > pageSize && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount} · {filteredItems.length} suppliers</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
