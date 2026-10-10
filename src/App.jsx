import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import DashboardLayout from './layouts/DashboardLayout'
import LoadingState from './components/LoadingState'
import InventoryPage from './pages/InventoryPage'
import InventoryOverview from './pages/InventoryOverview'
import InventoryProducts from './pages/InventoryProducts'
import InventoryCategories from './pages/InventoryCategories'
import InventorySuppliers from './pages/InventorySuppliers'
import InventoryMovements from './pages/InventoryMovements'
import InventoryLowStock from './pages/InventoryLowStock'
import PurchaseOrders from './pages/PurchaseOrders'
import Login from './pages/Login'
import Register from './pages/Register'
import Settings from './pages/Settings'
import POS from './pages/POS'
import Sales from './pages/Sales'
import SaleDetails from './pages/SaleDetails'
import Purchases from './pages/Purchases'
import PurchaseNew from './pages/PurchaseNew'
import PurchaseDetails from './pages/PurchaseDetails'
import Customers from './pages/Customers'
import CustomerDetails from './pages/CustomerDetails'
import Payments from './pages/Payments'
import Returns from './pages/Returns'
import Expenses from './pages/Expenses'
import Reports from './pages/Reports'
import AuditLogs from './pages/AuditLogs'
import Users from './pages/Users'
import { ProtectedRoute, PublicRoute, RoleGuard } from './routes/RouteGuards'
import './App.css'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const LandingPage = lazy(() => import('./pages/LandingPage'))

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/" element={<Suspense fallback={<LoadingState label="Loading The Orvion POS…" />}><LandingPage /></Suspense>} />
            <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
            <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
            <Route element={<ProtectedRoute />}>
              <Route element={<DashboardLayout />}>
                <Route path="dashboard" element={<Suspense fallback={<LoadingState label="Loading dashboard…" />}><Dashboard /></Suspense>} />
                <Route path="settings" element={<Settings />} />
                <Route path="pos" element={<POS />} />
                <Route path="sales" element={<Sales />} />
                <Route path="sales/:saleId" element={<SaleDetails />} />
                <Route path="returns" element={<Returns />} />
                <Route path="inventory" element={<InventoryPage />}>
                  <Route index element={<InventoryOverview />} />
                  <Route path="products" element={<InventoryProducts />} />
                  <Route path="categories" element={<InventoryCategories />} />
                  <Route path="suppliers" element={<InventorySuppliers />} />
                  <Route path="movements" element={<InventoryMovements />} />
                  <Route path="low-stock" element={<InventoryLowStock />} />
                  <Route element={<RoleGuard roles={['Owner', 'Admin', 'Manager']} />}>
                    <Route path="orders" element={<PurchaseOrders />} />
                  </Route>
                </Route>
                <Route path="purchases" element={<Purchases />} />
                <Route path="purchases/new" element={<PurchaseNew />} />
                <Route path="purchases/:purchaseId" element={<PurchaseDetails />} />
                <Route path="customers" element={<Customers />} />
                <Route path="customers/:customerId" element={<CustomerDetails />} />
                <Route path="payments" element={<Payments />} />
                <Route path="suppliers" element={<Navigate to="/inventory/suppliers" replace />} />
                <Route element={<RoleGuard roles={['Owner', 'Admin', 'Manager']} />}>
                  <Route path="expenses" element={<Expenses />} />
                  <Route path="reports" element={<Reports />} />
                </Route>
                <Route element={<RoleGuard roles={['Owner', 'Admin']} />}>
                  <Route path="users" element={<Users />} />
                  <Route path="audit-logs" element={<AuditLogs />} />
                </Route>
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
