import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, Store } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { useToast } from '../context/useToast'
import { getApiErrorMessage } from '../services/api'

export default function Login() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()

  async function submit(event) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await login(form)
      navigate('/', { replace: true })
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-card">
        <Link className="auth-brand" to="/"><span className="brand-mark"><Store size={19} /></span>Northstar<span className="brand-accent">.</span></Link>
        <div className="auth-heading"><span className="eyebrow">WELCOME BACK</span><h1>Sign in to your workspace</h1><p>Manage your business from one clear, connected place.</p></div>
        <form onSubmit={submit} className="auth-form">
          <label>Email address<input type="email" autoComplete="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="you@business.com" /></label>
          <label>Password<span className="password-field"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Enter your password" /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
          <button className="primary-button auth-submit" disabled={submitting}>{submitting ? <><span className="button-spinner" />Signing in…</> : <>Sign in <ArrowRight size={17} /></>}</button>
        </form>
        <p className="auth-switch">New to Northstar? <Link to="/register">Create your workspace</Link></p>
      </section>
      <aside className="auth-aside"><div className="auth-aside-mark"><Store size={22} /></div><div><span>THE BUSINESS WORKSPACE</span><h2>Run your store with a little more clarity.</h2><p>A thoughtful foundation for managing your business, team, and day-to-day operations.</p></div><small>Secure workspace access · Built for growing businesses</small></aside>
    </main>
  )
}
