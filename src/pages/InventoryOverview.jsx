import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Box, DollarSign, PackageSearch, ShieldAlert, Warehouse } from 'lucide-react'
import { inventoryService } from '../services/inventoryService'
import { formatCurrency } from '../utils/formatters'

const iconMap = {
  total_products: PackageSearch,
  inventory_value: DollarSign,
  low_stock: ShieldAlert,
  out_of_stock: Box,
  total_stock_units: Warehouse,
  category_count: Warehouse,
}

const metricLabels = {
  total_products: 'Total products',
  inventory_value: 'Inventory value',
  low_stock: 'Low stock',
  out_of_stock: 'Out of stock',
  total_stock_units: 'Total stock units',
  category_count: 'Categories',
}

export default function InventoryOverview() {
  const [summary, setSummary] = useState(null)
  const [lowStock, setLowStock] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    Promise.all([
      inventoryService.getSummary(),
      inventoryService.getLowStock(),
      inventoryService.getProducts({ page: 1, limit: 10 }),
    ])
      .then(([summaryData, lowStockData, productData]) => {
        if (active) {
          setSummary(summaryData)
          setLowStock(lowStockData)
          setProducts(productData.items || [])
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  if (loading || !summary) {
    return <div className="panel skeleton" style={{ minHeight: 220 }} />
  }

  const stats = [
    { key: 'total_products', value: summary.total_products },
    { key: 'inventory_value', value: formatCurrency(summary.inventory_value) },
    { key: 'low_stock', value: summary.low_stock },
    { key: 'out_of_stock', value: summary.out_of_stock },
    { key: 'total_stock_units', value: summary.total_stock_units },
    { key: 'category_count', value: summary.category_count },
  ]

  return (
    <div className="inventory-overview">
      <section className="kpi-grid">
        {stats.map(({ key, value }) => {
          const Icon = iconMap[key]
          return (
            <article key={key} className="kpi-card">
              <div className="kpi-icon blue"><Icon size={18} /></div>
              <div className="kpi-copy">
                <span>{metricLabels[key]}</span>
                <strong>{value}</strong>
              </div>
            </article>
          )
        })}
      </section>

      <section className="panel inventory-panel inventory-overview-products">
        <div className="panel-heading">
          <div>
            <h2>Products</h2>
            <p>Your latest inventory items and stock levels.</p>
          </div>
          <Link className="subtle-action" to="/inventory/products">View all products</Link>
        </div>
        <div className="data-table">
          <table>
            <thead>
              <tr><th>Product</th><th>SKU</th><th>Category</th><th>Cost</th><th>Selling price</th><th>Stock</th><th>Status</th></tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr><td colSpan="7" className="empty-cell">No products have been added yet.</td></tr>
              ) : products.map((item) => (
                <tr key={item.id}>
                  <td><div className="product-name-cell"><strong>{item.name}</strong>{item.brand && <small>{item.brand}</small>}</div></td>
                  <td><span className="sku-chip">{item.sku}</span></td>
                  <td>{item.category_name || '—'}</td>
                  <td className="numeric-cell">{formatCurrency(item.cost_price)}</td>
                  <td className="numeric-cell">{formatCurrency(item.selling_price)}</td>
                  <td className="numeric-cell"><strong>{Number(item.current_stock || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong><small className="table-subtext">{item.unit}</small></td>
                  <td><span className={`stock-state ${item.stock_status === 'LOW_STOCK' ? 'warning' : item.stock_status === 'OUT_OF_STOCK' ? 'danger' : 'success'}`}>{item.stock_status === 'LOW_STOCK' ? 'Low stock' : item.stock_status === 'OUT_OF_STOCK' ? 'Out of stock' : 'In stock'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel inventory-panel">
        <div className="panel-heading">
          <div>
            <h2>Low-stock watchlist</h2>
            <p>Products approaching or below their minimum stock levels.</p>
          </div>
        </div>
        {lowStock.length === 0 ? (
          <div className="empty-state">No low-stock items right now.</div>
        ) : (
          <div className="data-table">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Current</th>
                  <th>Minimum</th>
                  <th>Required</th>
                </tr>
              </thead>
              <tbody>
                {lowStock.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.sku}</td>
                    <td>{item.current_stock}</td>
                    <td>{item.minimum_stock}</td>
                    <td>{item.required_quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
