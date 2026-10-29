import { useEffect, useState } from 'react'
import { Eye, EyeOff, PencilLine, Plus, Search, Users as UsersIcon } from 'lucide-react'
import { useToast } from '../context/useToast'
import { getApiErrorMessage } from '../services/api'
import { userService } from '../services/userService'
import PasswordRequirements, { isStrongPassword } from '../components/PasswordRequirements'
import StaffActivationPanel from '../components/StaffActivationPanel'

const roles = ['Cashier', 'Inventory Manager', 'Manager']
const emptyForm = { name: '', email: '', password: '', role: 'Cashier', is_active: true }

export default function Users() {
  const { notify } = useToast()
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 10
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [reload, setReload] = useState(0)
  const [showPassword, setShowPassword] = useState(false)
  const [temporaryPassword, setTemporaryPassword] = useState(null)
  const filteredUsers = users.filter((account) => `${account.name} ${account.email} ${account.role} ${account.is_active ? 'active' : 'inactive'}`.toLowerCase().includes(search.trim().toLowerCase()))
  const pageCount = Math.max(1, Math.ceil(filteredUsers.length / pageSize))
  const pageUsers = filteredUsers.slice((page - 1) * pageSize, page * pageSize)

  useEffect(() => {
    let active = true
    userService.list()
      .then((items) => { if (active) { setUsers(items); setError('') } })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reload])

  function openForm(account = null) {
    setEditing(account)
    setForm(account
      ? { name: account.name, email: account.email, password: '', role: account.role, is_active: account.is_active }
      : { ...emptyForm })
    setShowForm(true)
  }

  async function refreshStaff() {
    const items = await userService.list()
    setUsers(items)
  }

  async function resetPassword(account) {
    try {
      const result = await userService.resetPassword(account.id)
      setTemporaryPassword({ name: account.name, password: result.temporary_password })
      notify('Temporary password created. It will only be shown in this dialog.')
      await refreshStaff()
    } catch (requestError) { notify(getApiErrorMessage(requestError), 'error') }
  }

  async function revokeSessions(account) {
    try { await userService.revokeSessions(account.id); notify(`Sessions revoked for ${account.name}.`); await refreshStaff() }
    catch (requestError) { notify(getApiErrorMessage(requestError), 'error') }
  }

  async function submit(event) {
    event.preventDefault()
    if (!editing && !isStrongPassword(form.password, 12)) {
      notify('Choose a temporary password that meets all the requirements.', 'error')
      return
    }
    setSaving(true)
    try {
      if (editing) {
        const { password: _password, ...update } = form
        await userService.update(editing.id, update)
      } else {
        const { is_active: _isActive, ...create } = form
        await userService.create(create)
      }
      notify(editing ? 'User updated.' : 'User added.')
      setShowForm(false)
      setReload((value) => value + 1)
    } catch (requestError) {
      notify(getApiErrorMessage(requestError), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="commerce-page">
      <div className="page-heading">
        <div><span className="eyebrow">WORKSPACE ACCESS</span><h1>Users</h1><p>Manage accounts and roles in this business workspace.</p></div>
        <button type="button" className="primary-button" onClick={() => openForm()}><Plus size={15} />Add user</button>
      </div>
      {error && <section className="panel report-error" role="alert"><span>{error}</span><button type="button" className="ghost-button" onClick={() => setReload((value) => value + 1)}>Retry</button></section>}
      {showForm && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowForm(false) }}>
        <section className="modal-card user-modal" role="dialog" aria-modal="true" aria-labelledby="user-form-title">
          <div className="user-modal-heading"><span className="eyebrow">WORKSPACE ACCESS</span><h2 id="user-form-title">{editing ? 'Edit user' : 'Add user'}</h2><p>Set up secure access for this business workspace.</p></div>
          <form className="user-form" onSubmit={submit}>
            <div className="user-form-fields">
              <label>Name<input required minLength="2" maxLength="120" autoComplete="name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Staff member name" /></label>
              <label>Gmail username<input required type="email" autoComplete="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="staff@gmail.com" /><small>Use a Gmail address. Ownership is not verified here.</small></label>
              {!editing && <>
                <label className="user-form-password">Temporary password<span className="password-field"><input required type={showPassword ? 'text' : 'password'} minLength="12" maxLength="128" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Create a temporary password" /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
                <PasswordRequirements password={form.password} minLength={12} className="user-password-requirements" />
              </>}
              <label className="user-form-role">Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>{(editing && !roles.includes(form.role) ? [...roles, form.role] : roles).map((role) => <option key={role} value={role}>{['Manager', 'Admin'].includes(role) ? `${role} (legacy)` : role}</option>)}</select></label>
              {editing && <label className="user-form-active"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />Active account</label>}
            </div>
            <div className="user-form-actions"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Cancel</button><button type="submit" className="primary-button" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create user'}</button></div>
          </form>
        </section>
      </div>}
      {temporaryPassword && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setTemporaryPassword(null) }}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="temporary-password-title"><div className="panel-heading"><div><h2 id="temporary-password-title">Temporary password</h2><p>Share this directly with {temporaryPassword.name}. They must choose a new password at next sign in.</p></div></div><label>Temporary password<input readOnly value={temporaryPassword.password} onFocus={(event) => event.target.select()} /></label><div className="form-actions"><button className="primary-button" onClick={() => setTemporaryPassword(null)}>Done</button></div></section></div>}
      <StaffActivationPanel />
      <section className="panel commerce-panel">
        <div className="panel-heading"><div><h2>Workspace users</h2><p>{users.length} accounts</p></div></div>
        <div className="table-toolbar"><label className="search-input"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search name, email, role, or status" aria-label="Search users" /></label></div>
        <div className="data-table"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Last login</th><th>Actions</th></tr></thead>
          <tbody>{loading
            ? <tr><td colSpan="6" className="empty-cell">Loading users…</td></tr>
            : filteredUsers.length === 0
              ? <tr><td colSpan="6" className="empty-cell"><UsersIcon size={18} />No users found.</td></tr>
              : pageUsers.map((account) => <tr key={account.id}><td>{account.name}</td><td>{account.email}</td><td>{account.role}</td><td><span className={`status-pill ${account.is_active ? 'status-paid' : 'status-unpaid'}`}>{account.is_active ? (account.is_activated ? 'Active' : 'Awaiting activation') : 'Inactive'}</span></td><td>{account.last_login_at ? new Date(account.last_login_at).toLocaleString() : 'Never'}</td><td className="table-actions">{account.role !== 'Owner' && <><button type="button" className="icon-button table-action" aria-label={`Edit ${account.name}`} onClick={() => openForm(account)}><PencilLine size={15} /></button><button type="button" className="ghost-button small" onClick={() => resetPassword(account)}>Reset password</button><button type="button" className="ghost-button small" onClick={() => revokeSessions(account)}>Revoke sessions</button></>}</td></tr>)}
          </tbody>
        </table></div>
        {filteredUsers.length > pageSize && <div className="pagination-row"><button className="ghost-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page} of {pageCount} · {filteredUsers.length} users</span><button className="ghost-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
      </section>
    </div>
  )
}
