import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { Bell, Boxes, ChartNoAxesColumn, ChevronDown, CircleDollarSign, ClipboardList, CreditCard, LayoutDashboard, Menu, PanelLeftClose, RotateCcw, Settings as SettingsIcon, ShieldCheck, ShoppingCart, Store, Truck, Users, Wallet, X } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { useToast } from '../context/useToast'

const links = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, end: true },
  { label: 'POS', to: '/pos', icon: ShoppingCart },
  { label: 'Sales', to: '/sales', icon: CircleDollarSign },
  { label: 'Returns', to: '/returns', icon: RotateCcw },
  { label: 'Inventory', to: '/inventory', icon: Boxes },
  { label: 'Purchases', to: '/purchases', icon: ClipboardList },
  { label: 'Customers', to: '/customers', icon: Users },
  { label: 'Suppliers', to: '/suppliers', icon: Truck },
  { label: 'Expenses', to: '/expenses', icon: Wallet },
  { label: 'Payments', to: '/payments', icon: CreditCard },
  { label: 'Reports', to: '/reports', icon: ChartNoAxesColumn },
  { label: 'Settings', to: '/settings', icon: SettingsIcon },
  { label: 'Users', to: '/users', icon: Users },
  { label: 'Audit logs', to: '/audit-logs', icon: ShieldCheck },
]

export default function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const { user, logout } = useAuth()
  const { notify } = useToast()
  const managerRoles = ['Owner', 'Admin', 'Manager']
  const isManager = managerRoles.includes(user?.role)
  const isAdmin = ['Owner', 'Admin'].includes(user?.role)
  const visibleLinks = links.filter(({ label }) => {
    if (['Expenses', 'Payments', 'Purchases', 'Suppliers', 'Inventory', 'Returns', 'Reports'].includes(label)) return isManager
    if (label === 'Users') return isAdmin
    if (label === 'Audit logs') return isAdmin
    return true
  })
  const initials = user?.name?.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase() || 'U'

  const handleLogout = () => {
    logout()
    notify('You have been signed out.')
  }

  return (
    <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
        <div className="brand">
          <span className="brand-mark"><Store size={19} /></span>
          {!collapsed && <span className="brand-name">Northstar<span>.</span></span>}
          <button className="mobile-close icon-button" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="workspace-switcher">
          <span className="business-avatar">{(user?.business_name || user?.name || 'B')[0].toUpperCase()}</span>
          {!collapsed && <><span className="workspace-name"><strong>{user?.business_name || 'Your business'}</strong><small>Business workspace</small></span><ChevronDown size={15} /></>}
        </div>
        <div className="nav-label">{!collapsed && 'Workspace'}</div>
        <nav className="side-nav" aria-label="Main navigation">
          {visibleLinks.map(({ label, to, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} title={collapsed ? label : undefined} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon size={18} /><span>{!collapsed && label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="plan-card"><span className="plan-indicator" />{!collapsed && <div><strong>Workspace ready</strong><small>Your business is set up</small></div>}</div>
          <div className="sidebar-user">
            <span className="avatar">{initials}</span>
            {!collapsed && <div className="sidebar-user-copy"><strong>{user?.name}</strong><small>{user?.role}</small></div>}
          </div>
        </div>
      </aside>

      {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu icon-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
            <button className="collapse-button icon-button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}><PanelLeftClose size={18} /></button>
            <span className="topbar-workspace">{user?.business_name || 'Business workspace'}</span>
          </div>
          <div className="topbar-actions">
            <button className="icon-button notification-button" aria-label="Notifications"><Bell size={19} /><i /></button>
            <div className="profile-menu-wrap">
              <button className="profile-trigger" onClick={() => setProfileOpen((value) => !value)} aria-expanded={profileOpen}>
                <span className="avatar">{initials}</span><span className="profile-trigger-copy"><strong>{user?.name}</strong><small>{user?.role}</small></span><ChevronDown size={15} />
              </button>
              {profileOpen && <div className="profile-dropdown"><div className="dropdown-identity"><strong>{user?.name}</strong><span>{user?.email}</span></div><NavLink to="/settings" onClick={() => setProfileOpen(false)}>Account settings</NavLink><button onClick={handleLogout}>Sign out</button></div>}
            </div>
          </div>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  )
}
