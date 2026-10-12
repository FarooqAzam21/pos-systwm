import { useEffect, useState } from 'react'
import { Building2, Check, CircleUserRound, Eye, EyeOff, LockKeyhole } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { useToast } from '../context/useToast'
import { getApiErrorMessage } from '../services/api'
import { businessService } from '../services/businessService'
import PasswordRequirements, { isStrongPassword } from '../components/PasswordRequirements'
import { CURRENCY_KEY } from '../utils/formatters'

const emptyBusiness = { business_name: '', owner_name: '', email: '', phone: '', address: '', city: '', tax_number: '', currency: 'USD', timezone: 'UTC', invoice_prefix: 'INV', invoice_footer: '', logo: '' }

export default function Settings() {
  const { user, updateAccount } = useAuth()
  const { notify } = useToast()
  const [business, setBusiness] = useState(emptyBusiness)
  const [account, setAccount] = useState({ name: user?.name || '', email: user?.email || '', current_password: '', new_password: '' })
  const [loading, setLoading] = useState(true)
  const [savingBusiness, setSavingBusiness] = useState(false)
  const [savingAccount, setSavingAccount] = useState(false)
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const canManageBusiness = ['Owner', 'Admin'].includes(user?.role)

  useEffect(() => {
    businessService.get()
      .then((data) => {
        localStorage.setItem(CURRENCY_KEY, data.currency || 'USD')
        setBusiness({ ...emptyBusiness, ...data, logo: data.logo || '' })
      })
      .catch((error) => notify(getApiErrorMessage(error), 'error'))
      .finally(() => setLoading(false))
  }, [notify, user?.name, user?.email])

  async function saveBusiness(event) {
    event.preventDefault()
    setSavingBusiness(true)
    try {
      const updated = await businessService.update({
        ...business,
        logo: business.logo || null,
        phone: business.phone || null,
        address: business.address || null,
        city: business.city || null,
        tax_number: business.tax_number || null,
        invoice_footer: business.invoice_footer || null,
      })
      setBusiness({ ...emptyBusiness, ...updated, logo: updated.logo || '' })
      localStorage.setItem(CURRENCY_KEY, updated.currency || 'USD')
      window.dispatchEvent(new Event('business-profile-updated'))
      notify('Business profile updated.')
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSavingBusiness(false)
    }
  }

  async function saveAccount(event) {
    event.preventDefault()
    if (account.new_password && !isStrongPassword(account.new_password)) {
      notify('Choose a new password that meets all the requirements.', 'error')
      return
    }
    setSavingAccount(true)
    try {
      await updateAccount({
        name: account.name,
        email: account.email,
        current_password: account.current_password || null,
        new_password: account.new_password || null,
      })
      setAccount((current) => ({ ...current, current_password: '', new_password: '' }))
      notify('Account details updated.')
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSavingAccount(false)
    }
  }

  return (
    <div className="settings-page">
      <div className="page-heading"><div><span className="eyebrow">PREFERENCES</span><h1>Settings</h1><p>Manage your business profile and personal account details.</p></div></div>
      {loading ? <div className="settings-skeleton"><div className="panel skeleton" /><div className="panel skeleton" /></div> : <>
        <form className="panel settings-card" onSubmit={saveBusiness}>
          <div className="settings-section-heading"><span className="section-icon business-icon"><Building2 size={19} /></span><div><h2>Business profile</h2><p>These details identify your business workspace.</p></div></div>
          {!canManageBusiness && <div className="permission-note"><LockKeyhole size={15} />Only an Owner or Admin can edit business information.</div>}
          <div className="settings-form-grid">
            <label>Business name<input required minLength="2" maxLength="160" disabled={!canManageBusiness} value={business.business_name} onChange={(event) => setBusiness({ ...business, business_name: event.target.value })} /></label>
            <label>Owner name<input required minLength="2" maxLength="120" disabled={!canManageBusiness} value={business.owner_name} onChange={(event) => setBusiness({ ...business, owner_name: event.target.value })} /></label>
            <label>Business email<input type="email" required disabled={!canManageBusiness} value={business.email} onChange={(event) => setBusiness({ ...business, email: event.target.value })} /></label>
            <label>Phone number<input type="tel" maxLength="40" disabled={!canManageBusiness} value={business.phone} onChange={(event) => setBusiness({ ...business, phone: event.target.value })} placeholder="+1 (555) 000-0000" /></label>
            <label className="field-span-2">Business address<input maxLength="500" disabled={!canManageBusiness} value={business.address} onChange={(event) => setBusiness({ ...business, address: event.target.value })} placeholder="Street address" /></label>
            <label>City<input maxLength="120" disabled={!canManageBusiness} value={business.city} onChange={(event) => setBusiness({ ...business, city: event.target.value })} /></label>
            <label>Tax number<input maxLength="80" disabled={!canManageBusiness} value={business.tax_number} onChange={(event) => setBusiness({ ...business, tax_number: event.target.value })} /></label>
            <label>Currency<select disabled={!canManageBusiness} value={business.currency} onChange={(event) => setBusiness({ ...business, currency: event.target.value })}><option value="USD">USD &mdash; US Dollar</option><option value="EUR">EUR &mdash; Euro</option><option value="GBP">GBP &mdash; British Pound</option><option value="CAD">CAD &mdash; Canadian Dollar</option><option value="AUD">AUD &mdash; Australian Dollar</option><option value="NZD">NZD &mdash; New Zealand Dollar</option><option value="INR">INR &mdash; Indian Rupee</option><option value="PKR">PKR &mdash; Pakistani Rupee</option><option value="BDT">BDT &mdash; Bangladeshi Taka</option><option value="LKR">LKR &mdash; Sri Lankan Rupee</option><option value="AED">AED &mdash; UAE Dirham</option><option value="SAR">SAR &mdash; Saudi Riyal</option><option value="JPY">JPY &mdash; Japanese Yen</option><option value="CNY">CNY &mdash; Chinese Yuan</option><option value="SGD">SGD &mdash; Singapore Dollar</option><option value="HKD">HKD &mdash; Hong Kong Dollar</option><option value="CHF">CHF &mdash; Swiss Franc</option><option value="SEK">SEK &mdash; Swedish Krona</option><option value="ZAR">ZAR &mdash; South African Rand</option><option value="BRL">BRL &mdash; Brazilian Real</option><option value="MXN">MXN &mdash; Mexican Peso</option><option value="TRY">TRY &mdash; Turkish Lira</option><option value="KWD">KWD &mdash; Kuwaiti Dinar</option></select></label>
            <label>Timezone<select disabled={!canManageBusiness} value={business.timezone} onChange={(event) => setBusiness({ ...business, timezone: event.target.value })}><option value="UTC">UTC</option><option value="America/New_York">America/New_York</option><option value="America/Chicago">America/Chicago</option><option value="America/Denver">America/Denver</option><option value="America/Los_Angeles">America/Los_Angeles</option><option value="Europe/London">Europe/London</option><option value="Europe/Paris">Europe/Paris</option><option value="Asia/Karachi">Asia/Karachi</option><option value="Asia/Kolkata">Asia/Kolkata</option><option value="Asia/Tokyo">Asia/Tokyo</option><option value="Australia/Sydney">Australia/Sydney</option></select></label>
            <label>Invoice prefix<input required minLength="1" maxLength="20" disabled={!canManageBusiness} value={business.invoice_prefix} onChange={(event) => setBusiness({ ...business, invoice_prefix: event.target.value })} /></label>
            <label className="field-span-2">Invoice footer<textarea rows={2} maxLength="500" disabled={!canManageBusiness} value={business.invoice_footer} onChange={(event) => setBusiness({ ...business, invoice_footer: event.target.value })} placeholder="Optional note printed at the bottom of invoices" /></label>
            <label className="field-span-2">Business logo URL <span className="field-help">This logo appears in your dashboard and invoices.</span><input type="url" maxLength="2048" disabled={!canManageBusiness} value={business.logo} onChange={(event) => setBusiness({ ...business, logo: event.target.value })} placeholder="https://example.com/logo.png" /></label>
          </div>
          {canManageBusiness && <div className="settings-form-footer"><span>Changes apply to this business workspace.</span><button className="primary-button" disabled={savingBusiness}>{savingBusiness ? <><span className="button-spinner" />Saving…</> : <><Check size={16} />Save business profile</>}</button></div>}
        </form>
        <form className="panel settings-card" onSubmit={saveAccount}>
          <div className="settings-section-heading"><span className="section-icon account-icon"><CircleUserRound size={19} /></span><div><h2>Your account</h2><p>Update your personal details and sign-in password.</p></div></div>
          <div className="settings-form-grid">
            <label>Name<input required minLength="2" maxLength="120" autoComplete="name" value={account.name} onChange={(event) => setAccount({ ...account, name: event.target.value })} /></label>
            <label>Email address<input type="email" required autoComplete="email" value={account.email} onChange={(event) => setAccount({ ...account, email: event.target.value })} /></label>
            <label>Current password<span className="password-field"><input type={showCurrentPassword ? 'text' : 'password'} autoComplete="current-password" minLength="1" maxLength="128" value={account.current_password} onChange={(event) => setAccount({ ...account, current_password: event.target.value })} placeholder="Required to change password" /><button type="button" aria-label={showCurrentPassword ? 'Hide password' : 'Show password'} onClick={() => setShowCurrentPassword((value) => !value)}>{showCurrentPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></span></label>
            <label>New password<span className="password-field"><input type={showNewPassword ? 'text' : 'password'} autoComplete="new-password" minLength="10" maxLength="128" value={account.new_password} onChange={(event) => setAccount({ ...account, new_password: event.target.value })} placeholder="Leave blank to keep current password" /><button type="button" aria-label={showNewPassword ? 'Hide password' : 'Show password'} onClick={() => setShowNewPassword((value) => !value)}>{showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></span></label>
            {account.new_password && <div className="field-span-2"><PasswordRequirements password={account.new_password} /></div>}
          </div>
          <div className="settings-form-footer"><span>Password changes require your current password.</span><button className="primary-button" disabled={savingAccount || Boolean(account.new_password && !isStrongPassword(account.new_password))}>{savingAccount ? <><span className="button-spinner" />Saving…</> : <><Check size={16} />Save account</>}</button></div>
        </form>
      </>}
    </div>
  )
}
