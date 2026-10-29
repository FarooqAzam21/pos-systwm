import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { useToast } from '../context/useToast'
import { getApiErrorMessage } from '../services/api'
import BrandLogo from '../components/BrandLogo'
import { authService } from '../services/authService'
import PasswordRequirements, { isStrongPassword } from '../components/PasswordRequirements'

export default function Login() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [stage, setStage] = useState('login')
  const [activationRequestId, setActivationRequestId] = useState('')
  const [otp, setOtp] = useState('')
  const [challengeToken, setChallengeToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const { login, finishActivation } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()

  async function submit(event) {
    event.preventDefault()
    setSubmitting(true)
    try {
      const result = await login(form)
      if (result.activation_required) {
        setActivationRequestId(result.request_id)
        setStage('activation')
        notify('Your owner must approve activation and generate a one-time code.')
      } else if (result.password_change_required) {
        setChallengeToken(result.challenge_token)
        setStage('password')
      } else {
        navigate('/dashboard', { replace: true })
      }
    } catch (error) {
      notify(getApiErrorMessage(error), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  async function submitActivation(event) {
    event.preventDefault()
    setSubmitting(true)
    try {
      const result = await authService.verifyActivation(activationRequestId, otp)
      setChallengeToken(result.challenge_token)
      setStage('password')
    } catch (error) { notify(getApiErrorMessage(error), 'error') }
    finally { setSubmitting(false) }
  }

  async function submitPassword(event) {
    event.preventDefault()
    if (newPassword !== confirmPassword) { notify('Passwords do not match.', 'error'); return }
    if (!isStrongPassword(newPassword)) { notify('Choose a password that meets all requirements.', 'error'); return }
    setSubmitting(true)
    try {
      await finishActivation({ challenge_token: challengeToken, new_password: newPassword })
      navigate('/dashboard', { replace: true })
    } catch (error) { notify(getApiErrorMessage(error), 'error') }
    finally { setSubmitting(false) }
  }

  return (
    <main className="auth-screen">
      <section className="auth-card">
        <Link className="auth-brand" to="/" aria-label="The Orvion POS home"><BrandLogo className="auth-brand-logo" /><span className="auth-brand-name">The Orvion<small>POS</small></span></Link>
        <div className="auth-heading"><span className="eyebrow">{stage === 'login' ? 'WELCOME BACK' : stage === 'activation' ? 'FIRST LOGIN ACTIVATION' : 'SECURE YOUR ACCOUNT'}</span><h1>{stage === 'login' ? 'Sign in to your workspace' : stage === 'activation' ? 'Enter your activation code' : 'Choose a new password'}</h1><p>{stage === 'login' ? 'Manage your business from one clear, connected place.' : stage === 'activation' ? 'Ask your workspace owner to approve your request and share the six-digit code.' : 'Set a personal password before accessing the workspace.'}</p></div>
        {stage === 'login' && <form onSubmit={submit} className="auth-form">
          <label>Email address<input type="email" autoComplete="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="you@business.com" /></label>
          <label>Password<span className="password-field"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Enter your password" /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
          <button className="primary-button auth-submit" disabled={submitting}>{submitting ? <><span className="button-spinner" />Signing in…</> : <>Sign in <ArrowRight size={17} /></>}</button>
        </form>}
        {stage === 'activation' && <form onSubmit={submitActivation} className="auth-form">
          <label>One-time code<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength="6" maxLength="6" required value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="6-digit code" /></label>
          <button className="primary-button auth-submit" disabled={submitting || otp.length !== 6}>{submitting ? 'Verifying…' : 'Verify code'}</button>
          <button type="button" className="ghost-button" onClick={() => { setStage('login'); setOtp('') }}>Back to sign in</button>
        </form>}
        {stage === 'password' && <form onSubmit={submitPassword} className="auth-form">
          <label>New password<input type="password" autoComplete="new-password" minLength="10" maxLength="128" required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
          <PasswordRequirements password={newPassword} />
          <label>Confirm new password<input type="password" autoComplete="new-password" minLength="10" maxLength="128" required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
          <button className="primary-button auth-submit" disabled={submitting}>{submitting ? 'Saving…' : 'Set password and continue'}</button>
        </form>}
        {stage === 'login' && <p className="auth-switch">New to The Orvion POS? <Link to="/register">Create your workspace</Link></p>}
      </section>
      <aside className="auth-aside"><BrandLogo className="auth-aside-logo" /><div><span>THE BUSINESS WORKSPACE</span><h2>Run your store with a little more clarity.</h2><p>A thoughtful foundation for managing your business, team, and day-to-day operations.</p></div><small>Secure workspace access · Built for growing businesses</small></aside>
    </main>
  )
}
