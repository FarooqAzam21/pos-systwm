import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, PencilLine, Plus, Search, UserRound } from 'lucide-react'
import { commerceService } from '../services/commerceService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { formatCurrency } from '../utils/formatters'

const emptyForm = { name: '', phone: '', email: '', address: '', city: '', tax_number: '', credit_limit: '0', notes: '' }

export default function Customers() {
  const [result, setResult] = useState({ items: [], total: 0 })
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [reload, setReload] = useState(0)
  const { notify } = useToast()

  useEffect(() => {
    let active = true
    setLoading(true)
    commerceService.getCustomers({ search, page, limit: 20 })
      .then((data) => { if (active) setResult(data) })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [search, page, reload, notify])

  function openForm(customer = null) {
    setEditing(customer)
    setForm(customer ? {
      name: customer.name,
      phone: customer.phone || '',
      email: customer.email || '',
      address: customer.address || '',
      city: customer.city || '',
      tax_number: customer.tax_number || '',
      credit_limit: customer.credit_limit,
      notes: customer.notes || '',
    } : emptyForm)
    setShowForm(true)
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value === '' ? null : value]))
      if (editing) await commerceService.updateCustomer(editing.id, payload)
      else await commerceService.createCustomer(payload)
      notify(editing ? 'Customer updated.' : 'Customer created.')
      setShowForm(false)
      setReload((value) => value + 1)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSaving(false)
    }
  }

  async function deactivate(customer) {
    if (!window.confirm(`Deactivate ${customer.name}?`)) return
    try {
      await commerceService.deactivateCustomer(customer.id)
      notify('Customer deactivated.')
      setReload((value) => value + 1)
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    }
  }

  const pageCount = Math.max(1, Math.ceil(result.total / 20))
  return (
    <div className="commerce-page">
      <div className="page-heading">
        <div><span className="eyebrow">RELATIONSHIPS</span><h1>Customers</h1><p>Manage customer details and outstanding balances.</p></div>
      </div>
      <div className="commerce-toolbar">
        <div className="search-input"><Search size={15} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search name, phone, or email" /></div>
        <button className="primary-button" onClick={() => openForm()}><Plus size={15} />Add customer</button>
      </div>
      <section className="panel commerce-panel">
        <div className="data-table"><table>
          <thead><tr><th>Customer</th><th>Phone</th><th>Email</th><th>Outstanding</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {loading ? <tr><td colSpan="6" className="empty-cell">Loading customers…</td></tr> :
              result.items.length === 0 ? <tr><td colSpan="6" className="empty-cell">No customers yet. Add your first customer to get started.</td></tr> :
                result.items.map((customer) => <tr key={customer.id}>
                  <td><strong>{customer.name}</strong></td><td>{customer.phone || '—'}</td><td>{customer.email || '—'}</td>
                  <td>{formatCurrency(customer.current_balance)}</td>
                  <td><span className={`tag ${customer.is_active ? 'success' : 'muted'}`}>{customer.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td><div className="row-actions">
                    <Link className="icon-button-inline" title="View customer" to={`/customers/${customer.id}`}><Eye size={14} /></Link>
                    <button className="icon-button-inline" title="Edit customer" onClick={() => openForm(customer)}><PencilLine size={14} /></button>
                    {customer.is_active && <button className="icon-button-inline danger" title="Deactivate customer" onClick={() => deactivate(customer)}><UserRound size={14} /></button>}
                  </div></td>
                </tr>)}
          </tbody>
        </table></div>
        {result.total > 20 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>

      {showForm && <div className="modal-backdrop" onClick={() => setShowForm(false)}><div className="modal-card large" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header"><h3>{editing ? 'Edit customer' : 'Add customer'}</h3><button className="ghost-button" onClick={() => setShowForm(false)}>Close</button></div>
        <form className="inventory-form two-column" onSubmit={submit}>
          <label>Name<input required maxLength="160" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label>Phone<input type="tel" inputMode="numeric" maxLength="11" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
          <label>Email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
          <label>City<input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} /></label>
          <label>Address<input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} /></label>
          <label>Tax number<input value={form.tax_number} onChange={(event) => setForm({ ...form, tax_number: event.target.value })} /></label>
          <label>Credit limit<input type="number" min="0" step="0.01" value={form.credit_limit} onChange={(event) => setForm({ ...form, credit_limit: event.target.value })} /></label>
          <label className="span-2">Notes<textarea rows={3} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
          <div className="modal-actions span-2"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Cancel</button><button className="primary-button" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create customer'}</button></div>
        </form>
      </div></div>}
    </div>
  )
}
