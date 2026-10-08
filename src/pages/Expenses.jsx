import { useEffect, useMemo, useState } from 'react'
import { PencilLine, Plus, Search, Trash2, Wallet } from 'lucide-react'
import { expenseService } from '../services/expenseService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'
import { useAuth } from '../context/useAuth'
import { formatCurrency } from '../utils/formatters'

const today = new Date().toISOString().slice(0, 10)
const emptyForm = {
  category_id: '',
  description: '',
  amount: '',
  expense_date: today,
  payment_method: 'cash',
  reference_number: '',
  notes: '',
}
const methods = ['cash', 'card', 'bank_transfer', 'mobile_wallet', 'other']
const formatAmount = formatCurrency

export default function Expenses() {
  const { user } = useAuth()
  const { notify } = useToast()
  const [result, setResult] = useState({ items: [], total: 0, total_amount: '0', category_breakdown: [] })
  const [categories, setCategories] = useState([])
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState({ start_date: '', end_date: '', category_id: '', payment_method: '' })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [newCategory, setNewCategory] = useState('')
  const [addingCategory, setAddingCategory] = useState(false)
  const canManage = ['Owner', 'Admin', 'Manager'].includes(user?.role)

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [search])

  useEffect(() => {
    let active = true
    expenseService.getCategories()
      .then((items) => { if (active) setCategories(items) })
      .catch((requestError) => { if (active) notify(getApiErrorMessage(requestError), 'error') })
    return () => { active = false }
  }, [notify, reload])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    expenseService.getExpenses({ ...filters, search: query, page, limit: 20 })
      .then((data) => { if (active) setResult(data) })
      .catch((requestError) => {
        if (active) {
          setError(getApiErrorMessage(requestError))
          setResult({ items: [], total: 0, total_amount: '0', category_breakdown: [] })
        }
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [filters, query, page, reload])

  const pageCount = Math.max(1, Math.ceil(result.total / 20))
  const categoriesByAmount = useMemo(() => result.category_breakdown || [], [result.category_breakdown])

  function openForm(expense = null) {
    setEditing(expense)
    setForm(expense ? {
      category_id: expense.category_id,
      description: expense.description,
      amount: String(expense.amount),
      expense_date: expense.expense_date,
      payment_method: expense.payment_method,
      reference_number: expense.reference_number || '',
      notes: expense.notes || '',
    } : { ...emptyForm, category_id: categories[0]?.id || '' })
    setShowForm(true)
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...form,
        amount: form.amount,
        reference_number: form.reference_number || null,
        notes: form.notes || null,
      }
      if (editing) await expenseService.updateExpense(editing.id, payload)
      else await expenseService.createExpense(payload)
      notify(editing ? 'Expense updated.' : 'Expense recorded.')
      setShowForm(false)
      setReload((value) => value + 1)
    } catch (requestError) {
      notify(getApiErrorMessage(requestError), 'error')
    } finally {
      setSaving(false)
    }
  }

  async function deleteExpense(expense) {
    if (!window.confirm(`Delete the expense "${expense.description}"? This action cannot be undone.`)) return
    try {
      await expenseService.deleteExpense(expense.id)
      notify('Expense deleted.')
      setReload((value) => value + 1)
    } catch (requestError) {
      notify(getApiErrorMessage(requestError), 'error')
    }
  }

  async function addCategory() {
    setAddingCategory(true)
    try {
      const created = await expenseService.createCategory({ name: newCategory })
      setCategories((items) => [...items, created].sort((left, right) => left.name.localeCompare(right.name)))
      setForm((current) => ({ ...current, category_id: created.id }))
      setNewCategory('')
      notify('Expense category added.')
    } catch (requestError) {
      notify(getApiErrorMessage(requestError), 'error')
    } finally {
      setAddingCategory(false)
    }
  }

  return (
    <div className="commerce-page">
      <div className="page-heading">
        <div><span className="eyebrow">BUSINESS MANAGEMENT</span><h1>Expenses</h1><p>Track operating costs and keep your business finances organized.</p></div>
        {canManage && <button className="primary-button" onClick={() => openForm()}><Plus size={15} />Add expense</button>}
      </div>
      <section className="kpi-grid commerce-kpis">
        <article className="kpi-card"><div className="kpi-icon rose"><Wallet size={18} /></div><div className="kpi-copy"><span>Filtered expenses</span><strong>{formatAmount(result.total_amount)}</strong><small>{result.total} records in this view</small></div></article>
        {categoriesByAmount.slice(0, 2).map((item) => <article className="kpi-card" key={item.category}><div className="kpi-icon amber"><Wallet size={18} /></div><div className="kpi-copy"><span>{item.category}</span><strong>{formatAmount(item.amount)}</strong><small>Category total for current filters</small></div></article>)}
      </section>
      <div className="commerce-toolbar expenses-toolbar">
        <div className="search-input"><Search size={15} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search description or reference" /></div>
        <label className="date-field">From<input type="date" value={filters.start_date} max={filters.end_date || undefined} onChange={(event) => { setFilters({ ...filters, start_date: event.target.value }); setPage(1) }} /></label>
        <label className="date-field">To<input type="date" value={filters.end_date} min={filters.start_date || undefined} onChange={(event) => { setFilters({ ...filters, end_date: event.target.value }); setPage(1) }} /></label>
        <select className="filter-select" aria-label="Filter by category" value={filters.category_id} onChange={(event) => { setFilters({ ...filters, category_id: event.target.value }); setPage(1) }}>
          <option value="">All categories</option>{categories.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}
        </select>
        <select className="filter-select" aria-label="Filter by payment method" value={filters.payment_method} onChange={(event) => { setFilters({ ...filters, payment_method: event.target.value }); setPage(1) }}>
          <option value="">All payment methods</option>{methods.map((method) => <option value={method} key={method}>{method.replaceAll('_', ' ')}</option>)}
        </select>
      </div>
      <section className="panel commerce-panel">
        {error && <div className="report-error" role="alert"><span>{error}</span><button className="ghost-button" onClick={() => setReload((value) => value + 1)}>Retry</button></div>}
        <div className="data-table"><table>
          <thead><tr><th>Date</th><th>Category</th><th>Description</th><th>Reference</th><th>Payment</th><th>Amount</th>{canManage && <th>Actions</th>}</tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={canManage ? 7 : 6} className="empty-cell">Loading expenses…</td></tr> :
              result.items.length === 0 ? <tr><td colSpan={canManage ? 7 : 6} className="empty-cell">No expenses found for these filters.</td></tr> :
                result.items.map((expense) => <tr key={expense.id}>
                  <td>{expense.expense_date}</td><td><span className="tag neutral">{expense.category_name}</span></td><td><strong>{expense.description}</strong>{expense.notes && <small className="expense-note">{expense.notes}</small>}</td>
                  <td>{expense.reference_number || '—'}</td><td>{expense.payment_method.replaceAll('_', ' ')}</td><td>{formatAmount(expense.amount)}</td>
                  {canManage && <td><div className="row-actions"><button className="icon-button-inline" title="Edit expense" onClick={() => openForm(expense)}><PencilLine size={14} /></button><button className="icon-button-inline danger" title="Delete expense" onClick={() => deleteExpense(expense)}><Trash2 size={14} /></button></div></td>}
                </tr>)}
          </tbody>
        </table></div>
        {result.total > 20 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>

      {showForm && <div className="modal-backdrop" onClick={() => setShowForm(false)}><div className="modal-card large" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header"><h3>{editing ? 'Edit expense' : 'Record expense'}</h3><button className="ghost-button" type="button" onClick={() => setShowForm(false)}>Close</button></div>
        <form className="inventory-form two-column" onSubmit={submit}>
          <label>Category<select required value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value })}><option value="">Choose category</option>{categories.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
          <label>Amount<input required type="number" min="0.01" step="0.01" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} /></label>
          <label>Description<input required minLength="2" maxLength="240" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <label>Expense date<input required type="date" value={form.expense_date} onChange={(event) => setForm({ ...form, expense_date: event.target.value })} /></label>
          <label>Payment method<select value={form.payment_method} onChange={(event) => setForm({ ...form, payment_method: event.target.value })}>{methods.map((method) => <option value={method} key={method}>{method.replaceAll('_', ' ')}</option>)}</select></label>
          <label>Reference number<input maxLength="100" value={form.reference_number} onChange={(event) => setForm({ ...form, reference_number: event.target.value })} /></label>
          <label className="span-2">Notes<textarea rows={3} maxLength="2000" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
          {!editing && <div className="new-category-row span-2">
            <label>Add a custom category<input maxLength="80" minLength="2" value={newCategory} onChange={(event) => setNewCategory(event.target.value)} placeholder="e.g. Equipment rental" /></label>
            <button type="button" className="ghost-button" onClick={addCategory} disabled={addingCategory || newCategory.trim().length < 2}>{addingCategory ? 'Adding…' : 'Add category'}</button>
          </div>}
          <div className="modal-actions span-2"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Cancel</button><button className="primary-button" disabled={saving || !form.category_id}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Record expense'}</button></div>
        </form>
      </div></div>}
    </div>
  )
}
