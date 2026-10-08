import { useEffect, useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { inventoryService } from '../services/inventoryService'

export default function InventoryMovements() {
  const [products, setProducts] = useState([])
  const [selectedProductId, setSelectedProductId] = useState('')
  const [movements, setMovements] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 10

  useEffect(() => {
    async function load() {
      const productList = await inventoryService.getProducts({ limit: 500 })
      setProducts(productList.items || [])
      if (productList.items?.[0]) {
        setSelectedProductId(productList.items[0].id)
      }
      setLoading(false)
    }

    load().catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedProductId) return

    async function loadMovements() {
      const data = await inventoryService.getMovements(selectedProductId)
      setMovements(data)
    }

    loadMovements().catch(() => setMovements([]))
  }, [selectedProductId])

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedProductId) || null,
    [products, selectedProductId],
  )
  const filteredMovements = movements.filter((item) => `${item.created_by_name || ''} ${item.movement_type} ${item.notes || ''} ${item.quantity} ${item.previous_stock} ${item.new_stock}`.toLowerCase().includes(search.trim().toLowerCase()))
  const pageCount = Math.max(1, Math.ceil(filteredMovements.length / pageSize))
  const pageMovements = filteredMovements.slice((page - 1) * pageSize, page * pageSize)

  if (loading) return <div className="panel skeleton" style={{ minHeight: 240 }} />

  return (
    <div className="inventory-subpage">
      <div className="subpage-toolbar">
        <label className="select-input">
          <span>Product</span>
          <select value={selectedProductId} onChange={(event) => setSelectedProductId(event.target.value)}>
            {products.map((product) => (
              <option key={product.id} value={product.id}>{product.name}</option>
            ))}
          </select>
        </label>
        <label className="search-input"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search stock movement" aria-label="Search stock movements" /></label>
      </div>

      <section className="panel inventory-panel">
        <div className="panel-heading">
          <div>
            <h2>Stock movements</h2>
            <p>{selectedProduct ? `Recent movement history for ${selectedProduct.name}` : 'Movement history'}</p>
          </div>
        </div>

        <div className="data-table">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Product</th>
                <th>Movement</th>
                <th>Quantity</th>
                <th>Previous Stock</th>
                <th>New Stock</th>
                <th>Reason</th>
                <th>User</th>
              </tr>
            </thead>
            <tbody>
              {filteredMovements.length === 0 ? (
                <tr><td colSpan="8" className="empty-cell">No stock activity for this product.</td></tr>
              ) : pageMovements.map((item) => (
                <tr key={item.id}>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                  <td>{item.product_name || '—'}</td>
                  <td><span className="tag neutral">{item.movement_type}</span></td>
                  <td>{item.quantity}</td>
                  <td>{item.previous_stock}</td>
                  <td>{item.new_stock}</td>
                  <td>{item.notes || '—'}</td>
                  <td>{item.created_by_name || 'System'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredMovements.length > pageSize && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount} · {filteredMovements.length} movements</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
