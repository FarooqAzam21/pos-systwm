import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Boxes, CircleDollarSign, PackageSearch, ShieldAlert, ShoppingBag, TrendingUp, CircleOff, ArrowDownRight, ArrowUpRight, ReceiptText, Users, Truck } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { commerceService } from '../services/commerceService'
import { reportService } from '../services/reportService'
import { getApiErrorMessage } from '../services/api'
import { useAuth } from '../context/useAuth'
import { formatCurrency } from '../utils/formatters'

const today = new Date()
const isoDate = (date) => date.toISOString().slice(0, 10)
const initialEnd = isoDate(today)
const initialStart = isoDate(new Date(today.getTime() - 6 * 86400000))
const currency = formatCurrency

export default function Dashboard() {
  const [range, setRange] = useState({ start_date: initialStart, end_date: initialEnd })
  const [rangePreset, setRangePreset] = useState('custom')
  const [overview, setOverview] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  const { user } = useAuth()
  useEffect(() => {
    let active = true
    setLoading(true)
    const request = user?.role === 'Cashier'
      ? commerceService.getDashboard(range).then((data) => [data, null])
      : Promise.all([commerceService.getDashboard(range), reportService.getDashboard(range)])
    request
      .then(([data, reportData]) => { if (active) { setOverview(data); setAnalytics(reportData); setError(null) } })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [range, reload, user?.role])

  const cards = overview && analytics ? [
    { label: 'Net revenue', value: currency(analytics.financials.net_revenue), icon: CircleDollarSign, tone: 'blue' },
    { label: 'COGS', value: currency(analytics.financials.cogs), icon: Boxes, tone: 'amber' },
    { label: 'Gross profit', value: currency(analytics.financials.gross_profit), icon: TrendingUp, tone: 'green' },
    { label: 'Operating expenses', value: currency(analytics.financials.operating_expenses), icon: ReceiptText, tone: 'rose' },
    { label: 'Net profit', value: currency(analytics.financials.net_profit), icon: ArrowUpRight, tone: 'violet' },
    { label: 'Gross margin', value: `${currency(analytics.financials.gross_margin_percent)}%`, icon: ArrowUpRight, tone: 'green' },
    { label: 'Net margin', value: `${currency(analytics.financials.net_margin_percent)}%`, icon: ArrowDownRight, tone: 'blue' },
    { label: 'Inventory cost value', value: currency(analytics.inventory.cost_value), icon: PackageSearch, tone: 'cyan' },
    { label: 'Low-stock products', value: analytics.inventory.low_stock, icon: ShieldAlert, tone: 'amber' },
    { label: 'Out-of-stock products', value: analytics.inventory.out_of_stock, icon: CircleOff, tone: 'rose' },
    { label: 'Customer outstanding', value: currency(analytics.customer_outstanding), icon: Users, tone: 'rose' },
    { label: 'Supplier outstanding', value: currency(analytics.supplier_outstanding), icon: Truck, tone: 'amber' },
    { label: "Today's transactions", value: overview.today.transactions, icon: ShoppingBag, tone: 'violet' },
  ] : overview ? [
    { label: "Today's sales", value: currency(overview.today.sales), icon: CircleDollarSign, tone: 'blue' },
    { label: "Today's transactions", value: overview.today.transactions, icon: ShoppingBag, tone: 'violet' },
  ] : []

  function applyRangePreset(value) {
    setRangePreset(value)
    if (value === 'custom') return
    const end = new Date(`${initialEnd}T00:00:00Z`)
    const start = new Date(end)
    if (value === 'week') start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7))
    if (value === 'month') start.setUTCDate(1)
    if (value === 'year') start.setUTCMonth(0, 1)
    setRange({ start_date: start.toISOString().slice(0, 10), end_date: initialEnd })
  }

  return (
    <div className="dashboard-page">
      <div className="page-heading dashboard-heading">
        <div><span className="eyebrow">BUSINESS OVERVIEW</span><h1>Dashboard</h1><p>Real sales and inventory performance from your workspace.</p></div>
        <div className="dashboard-range"><label>Period<select value={rangePreset} onChange={(event) => applyRangePreset(event.target.value)}><option value="today">Today</option><option value="week">This week</option><option value="month">This month</option><option value="year">This year</option><option value="custom">Custom range</option></select></label><label>From<input type="date" value={range.start_date} max={range.end_date} onChange={(event) => { setRangePreset('custom'); setRange({ ...range, start_date: event.target.value }) }} /></label><label>To<input type="date" value={range.end_date} min={range.start_date} onChange={(event) => { setRangePreset('custom'); setRange({ ...range, end_date: event.target.value }) }} /></label></div>
      </div>
      {loading ? <section className="kpi-grid">{Array.from({ length: 8 }, (_, index) => <div className="kpi-card skeleton" key={index} />)}</section> :
        error ? <section className="panel dashboard-status" role="alert"><p>{error}</p><button className="primary-button" onClick={() => setReload((value) => value + 1)}>Retry</button></section> :
          overview && analytics && <>
            <section className="kpi-grid dashboard-kpis">{cards.map(({ label, value, icon: Icon, tone }) => <article className="kpi-card" key={label}><div className={`kpi-icon ${tone}`}><Icon size={19} /></div><div className="kpi-copy"><span>{label}</span><strong>{value}</strong></div></article>)}</section>
            <section className="charts-grid commerce-chart-grid">
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Sales trend</h2><p>Net sales recorded per day.</p></div></div>
                {overview.sales_trend.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={overview.sales_trend}><CartesianGrid vertical={false} stroke="#eef0f4" /><XAxis dataKey="date" tickFormatter={(date) => date.slice(5)} /><YAxis /><Tooltip formatter={(value) => currency(value)} /><Area type="monotone" dataKey="sales" name="Sales" stroke="#5064e9" fill="#5064e933" /></AreaChart></ResponsiveContainer></div> : <div className="dashboard-status">No sales recorded in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Gross profit trend</h2><p>Sales less cost of goods sold. Operating expenses excluded.</p></div></div>
                {analytics.profit_trend.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analytics.profit_trend}><CartesianGrid vertical={false} stroke="#eef0f4" /><XAxis dataKey="date" tickFormatter={(date) => date.slice(5)} /><YAxis /><Tooltip formatter={(value) => currency(value)} /><Area type="monotone" dataKey="profit" name="Net profit" stroke="#31a47b" fill="#31a47b33" /></AreaChart></ResponsiveContainer></div> : <div className="dashboard-status">No profit recorded in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Expense trend</h2><p>Operating expenses recorded per day.</p></div></div>
                {analytics.expense_trend.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analytics.expense_trend}><CartesianGrid vertical={false} stroke="#eef0f4" /><XAxis dataKey="date" tickFormatter={(date) => date.slice(5)} /><YAxis /><Tooltip formatter={(value) => currency(value)} /><Area type="monotone" dataKey="expenses" name="Expenses" stroke="#dd836d" fill="#dd836d33" /></AreaChart></ResponsiveContainer></div> : <div className="dashboard-status">No expenses recorded in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Revenue vs expenses</h2><p>Net revenue compared to operating costs.</p></div></div>
                {analytics.revenue_vs_expenses.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analytics.revenue_vs_expenses}><CartesianGrid vertical={false} stroke="#eef0f4" /><XAxis dataKey="date" tickFormatter={(date) => date.slice(5)} /><YAxis /><Tooltip formatter={(value) => currency(value)} /><Area type="monotone" dataKey="revenue" name="Net revenue" stroke="#5064e9" fill="#5064e933" /><Area type="monotone" dataKey="expenses" name="Expenses" stroke="#dd836d" fill="#dd836d33" /></AreaChart></ResponsiveContainer></div> : <div className="dashboard-status">No financial activity in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Top products</h2><p>Best-selling products by revenue.</p></div></div>
                {overview.top_products.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><BarChart data={overview.top_products} layout="vertical" margin={{ left: 12, right: 18 }}><CartesianGrid horizontal={false} stroke="#eef0f4" /><XAxis type="number" /><YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => currency(value)} /><Bar dataKey="revenue" name="Revenue" fill="#5064e9" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div> : <div className="dashboard-status">No product sales in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Top categories</h2><p>Revenue less cost of goods sold.</p></div></div>
                {analytics.top_categories.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><BarChart data={analytics.top_categories} layout="vertical" margin={{ left: 12, right: 18 }}><CartesianGrid horizontal={false} stroke="#eef0f4" /><XAxis type="number" /><YAxis type="category" dataKey="product" width={120} tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => currency(value)} /><Bar dataKey="revenue" name="Revenue" fill="#31a47b" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div> : <div className="dashboard-status">No category sales in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Low-stock products</h2><p>Products at or below their minimum stock level.</p></div></div>
                {analytics.low_stock_products.length ? <div className="dashboard-list">{analytics.low_stock_products.map((item) => <div key={item.sku}><span><strong>{item.name}</strong><small>{item.sku} · minimum {item.minimum_stock}</small></span><b>{item.current_stock} left</b></div>)}</div> : <div className="dashboard-status">No products are low on stock.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Customer sales</h2><p>Highest customer sales in this date range.</p></div></div>
                {analytics.customer_sales.length ? <div className="dashboard-list">{analytics.customer_sales.map((item) => <div key={item.customer}><span><strong>{item.customer}</strong></span><b>{currency(item.sales)}</b></div>)}</div> : <div className="dashboard-status">No customer sales in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Payment methods</h2><p>Incoming payment amounts in this date range.</p></div></div>
                {analytics.payment_methods.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><PieChart><Tooltip formatter={(value) => currency(value)} /><Pie data={analytics.payment_methods} dataKey="amount" nameKey="method" outerRadius={82} label={({ name }) => name.replaceAll('_', ' ')}>{analytics.payment_methods.map((item, index) => <Cell key={item.method} fill={['#5064e9', '#31a47b', '#dca844', '#dd836d', '#8b66d5'][index % 5]} />)}</Pie></PieChart></ResponsiveContainer></div> : <div className="dashboard-status">No payments in this date range.</div>}
              </article>
              <article className="panel chart-panel"><div className="panel-heading"><div><h2>Purchase trend</h2><p>Supplier purchases recorded per day.</p></div></div>
                {analytics.purchase_trend.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analytics.purchase_trend}><CartesianGrid vertical={false} stroke="#eef0f4" /><XAxis dataKey="date" tickFormatter={(date) => date.slice(5)} /><YAxis /><Tooltip formatter={(value) => currency(value)} /><Area type="monotone" dataKey="purchases" name="Purchases" stroke="#8b66d5" fill="#8b66d533" /></AreaChart></ResponsiveContainer></div> : <div className="dashboard-status">No purchases recorded in this date range.</div>}
              </article>
            </section>
            <section className="panel commerce-panel dashboard-recent"><div className="panel-heading"><div><h2>Recent sales</h2><p>Latest recorded transactions.</p></div><Link to="/sales">View all</Link></div>
              <div className="data-table"><table><thead><tr><th>Invoice</th><th>Customer</th><th>Date</th><th>Total</th><th>Paid</th><th>Outstanding</th><th>Profit</th></tr></thead><tbody>
                {overview.recent_sales.length ? overview.recent_sales.map((sale) => <tr key={sale.id}><td><Link to={`/sales/${sale.id}`}>{sale.invoice_number}</Link></td><td>{sale.customer_name || 'Walk-in'}</td><td>{new Date(sale.sale_date).toLocaleString()}</td><td>{currency(sale.total_amount)}</td><td>{currency(sale.paid_amount)}</td><td>{currency(sale.outstanding_amount)}</td><td>{currency(sale.gross_profit)}</td></tr>) : <tr><td colSpan="7" className="empty-cell">No sales recorded yet.</td></tr>}
              </tbody></table></div>
            </section>
          </>}
      {!loading && !error && overview && !analytics && <>
        <section className="kpi-grid">{cards.map(({ label, value, icon: Icon, tone }) => <article className="kpi-card" key={label}><div className={`kpi-icon ${tone}`}><Icon size={19} /></div><div className="kpi-copy"><span>{label}</span><strong>{value}</strong></div></article>)}</section>
        <article className="panel chart-panel"><div className="panel-heading"><div><h2>Sales trend</h2><p>Sales recorded per day in the selected date range.</p></div></div>
          {overview.sales_trend.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={overview.sales_trend}><CartesianGrid vertical={false} stroke="#eef0f4" /><XAxis dataKey="date" tickFormatter={(date) => date.slice(5)} /><YAxis /><Tooltip formatter={(value) => currency(value)} /><Area type="monotone" dataKey="sales" name="Sales" stroke="#5064e9" fill="#5064e933" /></AreaChart></ResponsiveContainer></div> : <div className="dashboard-status">No sales recorded in this date range.</div>}
        </article>
      </>}
    </div>
  )
}
