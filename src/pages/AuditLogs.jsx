import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { reportService } from '../services/reportService'
import { getApiErrorMessage } from '../services/api'
import { useToast } from '../context/useToast'

export default function AuditLogs() {
  const { notify } = useToast()
  const [filters, setFilters] = useState({ start_date: '', end_date: '', entity_type: '' })
  const [search, setSearch] = useState('')
  const [result, setResult] = useState({ items: [], total: 0 })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    reportService.getAuditLogs({ ...filters, search, page, limit: 50 })
      .then((data) => { if (active) setResult(data) })
      .catch((requestError) => {
        if (active) {
          setError(getApiErrorMessage(requestError))
          notify(getApiErrorMessage(requestError), 'error')
        }
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [filters, search, page, reload, notify])

  const pageCount = Math.max(1, Math.ceil(result.total / 50))
  return (
    <div className="commerce-page">
      <div className="page-heading"><div><span className="eyebrow">SECURITY & GOVERNANCE</span><h1>Audit logs</h1><p>Review important actions performed in this business workspace.</p></div></div>
      <div className="commerce-toolbar audit-filters">
        <label className="date-field">From<input type="date" value={filters.start_date} max={filters.end_date || undefined} onChange={(event) => { setFilters({ ...filters, start_date: event.target.value }); setPage(1) }} /></label>
        <label className="date-field">To<input type="date" value={filters.end_date} min={filters.start_date || undefined} onChange={(event) => { setFilters({ ...filters, end_date: event.target.value }); setPage(1) }} /></label>
        <select className="filter-select" aria-label="Filter by entity" value={filters.entity_type} onChange={(event) => { setFilters({ ...filters, entity_type: event.target.value }); setPage(1) }}>
          <option value="">All entities</option>{['product', 'stock', 'purchase', 'sale', 'sale_return', 'customer_payment', 'supplier_payment', 'expense', 'expense_category', 'business', 'user'].map((item) => <option value={item} key={item}>{item.replaceAll('_', ' ')}</option>)}
        </select>
      </div>
      <section className="panel commerce-panel">
        {error && <div className="report-error" role="alert"><span>{error}</span><button className="ghost-button" onClick={() => setReload((value) => value + 1)}>Retry</button></div>}
        <div className="table-toolbar"><label className="search-input"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search actions, entities, descriptions" aria-label="Search audit logs" /></label></div>
        <div className="data-table"><table><thead><tr><th>Timestamp</th><th>User</th><th>Action</th><th>Entity</th><th>Description</th><th>Entity ID</th></tr></thead>
          <tbody>{loading ? <tr><td colSpan="6" className="empty-cell">Loading audit activity…</td></tr> :
            result.items.length === 0 ? <tr><td colSpan="6" className="empty-cell">No audit events match these filters.</td></tr> :
              result.items.map((item) => <tr key={item.id}><td>{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td><td>{item.user_name || 'Former user'}</td><td><span className="tag neutral">{item.action}</span></td><td>{item.entity_type.replaceAll('_', ' ')}</td><td>{item.description}</td><td>{item.entity_id || '—'}</td></tr>)}
          </tbody>
        </table></div>
        {result.total > 50 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
