import { useEffect, useState } from 'react'
import { AlertTriangle, PackagePlus, Search } from 'lucide-react'
import { inventoryService } from '../services/inventoryService'
import { useNavigate } from 'react-router-dom'

export default function InventoryLowStock() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 10

  useEffect(() => {
    inventoryService.getLowStock()
      .then((data) => setItems(data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="panel skeleton" style={{ minHeight: 220 }} />

  const filteredItems = items.filter((item) => `${item.name} ${item.sku} ${item.supplier_name || ''} ${item.stock_status}`.toLowerCase().includes(search.trim().toLowerCase()))
  const pageCount = Math.max(1, Math.ceil(filteredItems.length / pageSize))
  const pageItems = filteredItems.slice((page - 1) * pageSize, page * pageSize)

  return (
    <div className="inventory-subpage">
      <section className="panel inventory-panel">
        <div className="panel-heading">
          <div>
            <h2>Low stock</h2>
            <p>Products that need restocking soon.</p>
          </div>
        </div>

        <div className="table-toolbar"><label className="search-input"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search products, SKU, or supplier" aria-label="Search low-stock products" /></label></div>

        <div className="data-table">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Current Stock</th>
                <th>Minimum Stock</th>
                <th>Required Quantity</th>
                <th>Supplier</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr><td colSpan="8" className="empty-cell">No low-stock items found.</td></tr>
              ) : pageItems.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.name}</strong></td>
                  <td>{item.sku}</td>
                  <td>{item.current_stock}</td>
                  <td>{item.minimum_stock}</td>
                  <td>{item.required_quantity}</td>
                  <td>{item.supplier_name || 'Unassigned'}</td>
                  <td><span className="tag warning">{item.stock_status}</span></td>
                  <td>
                    <button className="primary-button small" type="button" onClick={() => navigate('/inventory/orders', { state: { restockProductId: item.id, restockQuantity: item.required_quantity, supplierName: item.supplier_name } })}>
                      <PackagePlus size={14} /> Restock
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredItems.length > pageSize && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount} · {filteredItems.length} products</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
