import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { useToast } from '../context/useToast'
import { getApiErrorMessage } from '../services/api'
import PasswordRequirements, { isStrongPassword } from '../components/PasswordRequirements'
import BrandLogo from '../components/BrandLogo'

export default function Register() {
  const [form, setForm] = useState({ business_name: '', owner_name: '', email: '', password: '', confirm_password: '' })
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const { register } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const passwordStrong = isStrongPassword(form.password)

  async function submit(event) {
    event.preventDefault()
    if (form.password !== form.confirm_password) {
      notify('Passwords do not match.', 'error')
      return
    }
    if (!passwordStrong) {
      notify('Choose a password that meets all the requirements.', 'error')
      return
    }
    setSubmitting(true)
    try {
      await register({ ...form, name: form.owner_name })
      notify('Your business workspace is ready.')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-card register-card">
        <Link className="auth-brand" to="/" aria-label="The Orvion POS home"><BrandLogo className="auth-brand-logo" /></Link>
        <div className="auth-heading"><span className="eyebrow">GET STARTED</span><h1>Create your business workspace</h1><p>Your business and owner account will be created together.</p></div>
        <form onSubmit={submit} className="auth-form">
          <label>Business name<input autoComplete="organization" required minLength="2" maxLength="160" value={form.business_name} onChange={(event) => setForm({ ...form, business_name: event.target.value })} placeholder="Northstar Market" /></label>
          <label>Owner name<input autoComplete="name" required minLength="2" maxLength="120" value={form.owner_name} onChange={(event) => setForm({ ...form, owner_name: event.target.value })} placeholder="Your full name" /></label>
          <label>Email address<input type="email" autoComplete="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="you@business.com" /></label>
          <div className="auth-form-row"><label>Password<span className="password-field"><input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required minLength="10" maxLength="128" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Create a strong password" /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label><label>Confirm password<span className="password-field"><input type={showConfirmPassword ? 'text' : 'password'} autoComplete="new-password" required minLength="10" maxLength="128" value={form.confirm_password} onChange={(event) => setForm({ ...form, confirm_password: event.target.value })} placeholder="Repeat password" /><button type="button" aria-label={showConfirmPassword ? 'Hide password' : 'Show password'} onClick={() => setShowConfirmPassword((value) => !value)}>{showConfirmPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label></div>
          <PasswordRequirements password={form.password} />
          <button className="primary-button auth-submit" disabled={submitting || !passwordStrong}>{submitting ? <><span className="button-spinner" />Creating workspace…</> : <>Create workspace <ArrowRight size={17} /></>}</button>
        </form>
        <p className="auth-switch">Already have a workspace? <Link to="/login">Sign in</Link></p>
      </section>
      <aside className="auth-aside"><BrandLogo className="auth-aside-logo" /><div><span>ONE WORKSPACE FOR YOUR BUSINESS</span><h2>A better foundation for your everyday business.</h2><p>Start with a private workspace for your business and build on it as you grow.</p></div><small>Your account is securely protected</small></aside>
    </main>
  )
}
