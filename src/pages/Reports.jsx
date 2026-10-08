import { useEffect, useMemo, useState } from 'react'
import { FileSpreadsheet, FileText, Search } from 'lucide-react'
import { getApiErrorMessage } from '../services/api'
import { reportService } from '../services/reportService'
import { businessService } from '../services/businessService'
import { useToast } from '../context/useToast'
import { useAuth } from '../context/useAuth'
import { formatCurrency } from '../utils/formatters'

const dateInTimezone = (timezone) => {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date())
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]))
  return `${values.year}-${values.month}-${values.day}`
}
const offsetDate = (value, days) => {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}
const reportTabs = [
  ['sales', 'Sales'],
  ['purchases', 'Purchases'],
  ['inventory', 'Inventory'],
  ['stock-movements', 'Stock movements'],
  ['expenses', 'Expenses'],
  ['product-profitability', 'Profitability'],
  ['category-performance', 'Categories'],
  ['customers', 'Customers'],
  ['suppliers', 'Suppliers'],
  ['payments', 'Payments'],
  ['profit-and-loss', 'P&L'],
  ['daily-closing', 'Daily closing'],
]
const pdfReports = new Set(['sales', 'purchases', 'expenses', 'inventory', 'product-profitability', 'profit-and-loss', 'daily-closing'])
const definitions = {
  sales: ['invoice', 'date', 'customer', 'cashier', 'subtotal', 'discount', 'tax', 'total', 'paid', 'outstanding', 'cogs', 'gross_profit', 'status'],
  purchases: ['invoice', 'date', 'supplier', 'subtotal', 'discount', 'tax', 'total', 'paid', 'outstanding', 'payment_status'],
  inventory: ['sku', 'barcode', 'product', 'category', 'current_stock', 'cost_price', 'selling_price', 'inventory_value', 'minimum_stock', 'stock_status'],
  expenses: ['date', 'category', 'description', 'amount', 'payment_method', 'created_by'],
  'product-profitability': ['product', 'units_sold', 'revenue', 'cogs', 'gross_profit', 'margin_percent'],
  'category-performance': ['category', 'units_sold', 'revenue', 'cogs', 'gross_profit', 'margin_percent'],
  customers: ['customer', 'transactions', 'total_purchases', 'total_paid', 'outstanding', 'returns', 'net_spending', 'last_purchase'],
  suppliers: ['supplier', 'purchases', 'paid', 'outstanding', 'purchase_count', 'latest_purchase'],
  payments: ['date', 'reference', 'party', 'type', 'reference_type', 'amount', 'payment_method', 'received_by'],
  'profit-and-loss': ['metric', 'amount'],
  'daily-closing': ['date', 'opening_cash', 'cash_sales', 'card_received', 'other_payments', 'customer_payments', 'refunds', 'expenses', 'expected_closing_cash', 'actual_closing_cash', 'variance', 'transactions', 'net_sales', 'cogs', 'gross_profit', 'net_profit', 'closed_by', 'closed_at', 'notes'],
}
const moneyFields = new Set(['subtotal', 'discount', 'tax', 'total', 'paid', 'outstanding', 'cogs', 'gross_profit', 'amount', 'inventory_value', 'cost_price', 'selling_price', 'revenue', 'total_purchases', 'total_paid', 'returns', 'net_spending', 'purchases', 'expenses', 'total_sales', 'total_returns', 'net_sales', 'cash_received', 'cash_sales', 'card_received', 'bank_transfer', 'mobile_wallet', 'other_payments', 'customer_payments', 'refunds', 'opening_cash', 'expected_closing_cash', 'actual_closing_cash', 'variance', 'net_profit'])
const formatValue = (field, value) => {
  if (value === null || value === undefined || value === '') return '—'
  if (moneyFields.has(field)) return formatCurrency(value)
  if (field === 'margin_percent') return `${Number(value).toFixed(2)}%`
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'string' && value.includes('T')) return new Date(value).toLocaleString()
  return String(value).replaceAll('_', ' ')
}

export default function Reports() {
  const { notify } = useToast()
  const { user } = useAuth()
  const [reportName, setReportName] = useState('sales')
  const [period, setPeriod] = useState('custom')
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    search: '',
    customer_id: '',
    cashier_id: '',
    supplier_id: '',
    category_id: '',
    product_id: '',
    payment_method: '',
    payment_status: '',
    status: '',
    payment_type: '',
    movement_type: '',
  })
  const [search, setSearch] = useState('')
  const [result, setResult] = useState({ items: [], total: 0, summary: {} })
  const [options, setOptions] = useState({ customers: [], users: [], suppliers: [], categories: [], products: [], expenseCategories: [] })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState('')
  const [reload, setReload] = useState(0)
  const [closingForm, setClosingForm] = useState({ opening_cash: '0.00', actual_closing_cash: '', notes: '' })
  const [savingClosing, setSavingClosing] = useState(false)
  const [businessReady, setBusinessReady] = useState(false)
  const canCloseDay = ['Owner', 'Admin', 'Manager'].includes(user?.role)

  useEffect(() => {
    let active = true
    businessService.get()
      .then((business) => {
        if (!active) return
        const today = dateInTimezone(business.timezone || 'UTC')
        setFilters((current) => ({ ...current, start_date: offsetDate(today, -6), end_date: today }))
        setBusinessReady(true)
      })
      .catch((requestError) => {
        if (active) {
          notify(getApiErrorMessage(requestError), 'error')
          const today = dateInTimezone('UTC')
          setFilters((current) => ({ ...current, start_date: offsetDate(today, -6), end_date: today }))
          setBusinessReady(true)
        }
      })
    return () => { active = false }
  }, [notify])

  useEffect(() => {
    let active = true
    reportService.getFilterOptions()
      .then((data) => { if (active) setOptions(data) })
      .catch((requestError) => { if (active) notify(getApiErrorMessage(requestError), 'error') })
    return () => { active = false }
  }, [notify])

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(filters.search.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [filters.search])

  const params = useMemo(() => {
    const values = { ...filters, search, page, limit: 50 }
    if (reportName === 'daily-closing') {
      values.report_date = filters.start_date
      values.start_date = filters.start_date
      values.end_date = filters.start_date
    }
    return values
  }, [filters, search, page, reportName])

  useEffect(() => {
    if (!businessReady) return undefined
    let active = true
    setLoading(true)
    setError('')
    reportService.get(reportName, params)
      .then((data) => {
        if (!active) return
        setResult(Array.isArray(data.items) ? data : { items: [], total: 0, summary: data })
      })
      .catch((requestError) => {
        if (active) {
          setError(getApiErrorMessage(requestError))
          setResult({ items: [], total: 0, summary: {} })
        }
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [businessReady, reportName, params, reload])

  const columns = definitions[reportName] || Object.keys(result.items[0] || {})
  const summary = Object.entries(result.summary || {}).filter(([, value]) => ['string', 'number'].includes(typeof value) && Number.isFinite(Number(value)))
  const pageCount = Math.max(1, Math.ceil(result.total / 50))
  const canSearch = ['sales', 'expenses', 'inventory', 'customers', 'suppliers'].includes(reportName)

  function setFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }))
    setPage(1)
  }

  function applyPeriod(value) {
    setPeriod(value)
    if (value === 'custom') return
    const today = filters.end_date
    const end = new Date(`${today}T00:00:00Z`)
    const start = new Date(end)
    if (value === 'week') start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7))
    if (value === 'month') start.setUTCDate(1)
    if (value === 'year') start.setUTCMonth(0, 1)
    setFilters((current) => ({ ...current, start_date: start.toISOString().slice(0, 10), end_date: today }))
    setPage(1)
  }

  async function download(format) {
    setExporting(format)
    try {
      const exportParams = reportName === 'daily-closing'
        ? { ...params, report_date: filters.start_date, start_date: filters.start_date, end_date: filters.start_date }
        : params
      const file = await reportService.export(reportName, format, exportParams)
      const url = URL.createObjectURL(file)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${reportName}-${filters.start_date}-to-${reportName === 'daily-closing' ? filters.start_date : filters.end_date}.${format}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      notify(getApiErrorMessage(requestError), 'error')
    } finally {
      setExporting('')
    }
  }

  async function closeDay(event) {
    event.preventDefault()
    setSavingClosing(true)
    try {
      const data = await reportService.closeDay({ report_date: filters.start_date, ...closingForm })
      setResult(data)
      notify('Daily closing saved.')
    } catch (requestError) {
      notify(getApiErrorMessage(requestError), 'error')
    } finally {
      setSavingClosing(false)
    }
  }

  return (
    <div className="commerce-page">
      <div className="page-heading">
        <div><span className="eyebrow">BUSINESS INTELLIGENCE</span><h1>Reports</h1><p>Financial and operational reporting for your business.</p></div>
      </div>
      <div className="report-tabs" role="tablist" aria-label="Report types">
        {reportTabs.map(([name, label]) => <button type="button" role="tab" aria-selected={reportName === name} className={reportName === name ? 'active' : ''} key={name} onClick={() => { setReportName(name); setPage(1) }}>{label}</button>)}
      </div>
      <section className="panel report-filter-panel">
        <div className="report-filters">
          {reportName === 'profit-and-loss' && <select className="filter-select" aria-label="Financial report period" value={period} onChange={(event) => applyPeriod(event.target.value)}><option value="today">Today</option><option value="week">This week</option><option value="month">This month</option><option value="year">This year</option><option value="custom">Custom range</option></select>}
          <label className="date-field">From<input type="date" value={filters.start_date} max={filters.end_date} onChange={(event) => { setPeriod('custom'); setFilter('start_date', event.target.value) }} /></label>
          <label className="date-field">To<input type="date" value={filters.end_date} min={filters.start_date} onChange={(event) => { setPeriod('custom'); setFilter('end_date', event.target.value) }} /></label>
          {canSearch && <label className="report-search"><Search size={15} /><input value={filters.search} onChange={(event) => setFilter('search', event.target.value)} placeholder="Search report" /></label>}
          {reportName === 'sales' && <>
            <select className="filter-select" aria-label="Filter by customer" value={filters.customer_id} onChange={(event) => setFilter('customer_id', event.target.value)}><option value="">All customers</option>{options.customers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <select className="filter-select" aria-label="Filter by cashier" value={filters.cashier_id} onChange={(event) => setFilter('cashier_id', event.target.value)}><option value="">All cashiers</option>{options.users.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
            <select className="filter-select" aria-label="Filter by payment method" value={filters.payment_method} onChange={(event) => setFilter('payment_method', event.target.value)}><option value="">All payment methods</option>{['cash', 'card', 'bank_transfer', 'mobile_wallet', 'other'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select>
            <select className="filter-select" aria-label="Filter by sale status" value={filters.status} onChange={(event) => setFilter('status', event.target.value)}><option value="">All statuses</option>{['completed', 'partially_returned', 'returned', 'voided'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select>
          </>}
          {reportName === 'purchases' && <><select className="filter-select" aria-label="Filter by supplier" value={filters.supplier_id} onChange={(event) => setFilter('supplier_id', event.target.value)}><option value="">All suppliers</option>{options.suppliers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><select className="filter-select" aria-label="Filter by payment status" value={filters.payment_status} onChange={(event) => setFilter('payment_status', event.target.value)}><option value="">All payment statuses</option>{['unpaid', 'partial', 'paid'].map((value) => <option key={value} value={value}>{value}</option>)}</select></>}
          {['expenses', 'inventory', 'product-profitability', 'category-performance'].includes(reportName) && <select className="filter-select" aria-label="Filter by category" value={filters.category_id} onChange={(event) => setFilter('category_id', event.target.value)}><option value="">All categories</option>{(reportName === 'expenses' ? options.expenseCategories : options.categories).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
          {reportName === 'expenses' && <select className="filter-select" aria-label="Filter by payment method" value={filters.payment_method} onChange={(event) => setFilter('payment_method', event.target.value)}><option value="">All payment methods</option>{['cash', 'card', 'bank_transfer', 'mobile_wallet', 'other'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select>}
          {reportName === 'payments' && <><select className="filter-select" aria-label="Filter by payment method" value={filters.payment_method} onChange={(event) => setFilter('payment_method', event.target.value)}><option value="">All payment methods</option>{['cash', 'card', 'bank_transfer', 'mobile_wallet', 'other'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select><select className="filter-select" aria-label="Filter by payment type" value={filters.payment_type} onChange={(event) => setFilter('payment_type', event.target.value)}><option value="">All types</option><option value="incoming">Incoming</option><option value="outgoing">Outgoing</option></select></>}
          {reportName === 'stock-movements' && <><select className="filter-select" aria-label="Filter by product" value={filters.product_id} onChange={(event) => setFilter('product_id', event.target.value)}><option value="">All products</option>{options.products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><select className="filter-select" aria-label="Filter by movement type" value={filters.movement_type} onChange={(event) => setFilter('movement_type', event.target.value)}><option value="">All movement types</option>{['opening_stock', 'purchase', 'sale', 'return', 'adjustment_in', 'adjustment_out', 'damage', 'transfer_in', 'transfer_out'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></>}
          <div className="report-export-actions">
            <button type="button" className="ghost-button" disabled={Boolean(exporting)} onClick={() => download('xlsx')}><FileSpreadsheet size={14} />{exporting === 'xlsx' ? 'Preparing…' : 'Export Excel'}</button>
            {pdfReports.has(reportName) && <button type="button" className="ghost-button" disabled={Boolean(exporting)} onClick={() => download('pdf')}><FileText size={14} />{exporting === 'pdf' ? 'Preparing…' : 'Export PDF'}</button>}
          </div>
        </div>
      </section>
      {summary.length > 0 && <section className="kpi-grid report-summary-grid">{summary.slice(0, 6).map(([key, value]) => <article className="report-summary-card" key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{formatValue(key, value)}</strong></article>)}</section>}
      {reportName === 'daily-closing' && canCloseDay && !result.summary?.closed_at && <form className="panel report-filter-panel" onSubmit={closeDay}>
        <div className="report-filters">
          <label>Opening cash<input type="number" min="0" step="0.01" required value={closingForm.opening_cash} onChange={(event) => setClosingForm((value) => ({ ...value, opening_cash: event.target.value }))} /></label>
          <label>Actual closing cash<input type="number" min="0" step="0.01" required value={closingForm.actual_closing_cash} onChange={(event) => setClosingForm((value) => ({ ...value, actual_closing_cash: event.target.value }))} /></label>
          <label className="report-search">Notes<input maxLength="2000" value={closingForm.notes} onChange={(event) => setClosingForm((value) => ({ ...value, notes: event.target.value }))} /></label>
          <button className="primary-button" disabled={savingClosing || loading}>{savingClosing ? 'Saving…' : 'Save daily closing'}</button>
        </div>
      </form>}
      <section className="panel commerce-panel">
        {error && <div className="report-error" role="alert"><span>{error}</span><button className="ghost-button" onClick={() => setReload((value) => value + 1)}>Retry</button></div>}
        <div className="data-table"><table><thead><tr>{columns.map((field) => <th key={field}>{field.replaceAll('_', ' ')}</th>)}</tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={Math.max(columns.length, 1)} className="empty-cell">Loading report…</td></tr> :
              result.items.length === 0 ? <tr><td colSpan={Math.max(columns.length, 1)} className="empty-cell">No records found for this report and date range.</td></tr> :
                result.items.map((row, rowIndex) => <tr key={row.id || row.invoice || `${reportName}-${rowIndex}`}>{columns.map((field) => <td key={field}>{formatValue(field, row[field])}</td>)}</tr>)}
          </tbody>
        </table></div>
        {result.total > 50 && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
