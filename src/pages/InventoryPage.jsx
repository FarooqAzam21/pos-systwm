import { Link, NavLink, Outlet } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { useAuth } from '../context/useAuth'

const tabs = [
  { label: 'Overview', to: '/inventory' },
  { label: 'Products', to: '/inventory/products' },
  { label: 'Categories', to: '/inventory/categories' },
  { label: 'Suppliers', to: '/inventory/suppliers' },
  { label: 'Stock Movements', to: '/inventory/movements' },
  { label: 'Low Stock', to: '/inventory/low-stock' },
]

export default function InventoryPage() {
  const { user } = useAuth()
  const canManageProducts = ['Owner', 'Admin', 'Manager'].includes(user?.role)

  return (
    <div className="inventory-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">INVENTORY</span>
          <h1>Inventory management</h1>
          <p>Track products, stock movement, suppliers, and low-stock items across your business.</p>
        </div>
        {canManageProducts && <Link className="primary-button" to="/inventory/products" state={{ openAddProduct: true }}><Plus size={15} />Add product</Link>}
      </div>
      <nav className="inventory-tabs" aria-label="Inventory sections">
        {tabs.map(({ label, to }) => (
          <NavLink key={to} to={to} end={to === '/inventory'} className={({ isActive }) => `inventory-tab ${isActive ? 'active' : ''}`}>
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
