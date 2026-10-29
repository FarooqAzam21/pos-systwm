import { useCallback, useEffect, useState } from 'react'
import { Copy } from 'lucide-react'
import { useToast } from '../context/useToast'
import { getApiErrorMessage } from '../services/api'
import { userService } from '../services/userService'

export default function StaffActivationPanel() {
  const { notify } = useToast()
  const [requests, setRequests] = useState([])
  const [codes, setCodes] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    const items = await userService.activationRequests()
    setRequests(items)
    setError('')
  }, [])

  useEffect(() => {
    let active = true
    userService.activationRequests()
      .then((items) => { if (active) { setRequests(items); setError('') } })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function issueCode(request) {
    try {
      let result
      try { result = await userService.generateActivationOtp(request.id) }
      catch { result = await userService.readActivationOtp(request.id) }
      setCodes((current) => ({ ...current, [request.id]: result.otp }))
      window.setTimeout(() => setCodes((current) => {
        const next = { ...current }
        delete next[request.id]
        return next
      }), 5 * 60 * 1000)
      await refresh()
    } catch (requestError) { notify(getApiErrorMessage(requestError), 'error') }
  }

  async function rejectRequest(request) {
    try {
      await userService.rejectActivation(request.id)
      setCodes((current) => { const next = { ...current }; delete next[request.id]; return next })
      notify('Activation request rejected.')
      await refresh()
    } catch (requestError) { notify(getApiErrorMessage(requestError), 'error') }
  }

  async function copyCode(request) {
    const code = codes[request.id]
    if (!code) return
    try {
      await navigator.clipboard.writeText(code)
      notify('Activation code copied. Share it privately with the staff member.')
    } catch {
      notify('Clipboard access is unavailable. Select and copy the displayed code.', 'error')
    }
  }

  return (
    <section className="panel commerce-panel">
      <div className="panel-heading"><div><h2>Staff first-login activation</h2><p>Generate a one-time code for a staff member who has signed in with their temporary password.</p></div></div>
      {error && <div className="report-error" role="alert"><span>{error}</span><button type="button" className="ghost-button" onClick={() => { setLoading(true); refresh().catch((requestError) => setError(getApiErrorMessage(requestError))).finally(() => setLoading(false)) }}>Retry</button></div>}
      {loading ? <div className="empty-cell">Loading activation requests…</div>
        : requests.length === 0 ? <div className="empty-cell">No staff activation requests are waiting.</div>
          : <div className="data-table"><table><thead><tr><th>Staff member</th><th>Role</th><th>Request</th><th>One-time code</th><th>Actions</th></tr></thead><tbody>
            {requests.map((request) => <tr key={request.id}>
              <td>{request.user.name}<small className="table-secondary">{request.user.email}</small></td>
              <td>{request.user.role}</td>
              <td>{request.status === 'otp_issued' ? 'Code generated' : 'Owner approval needed'}</td>
              <td>{codes[request.id] ? <span className="activation-code-wrap"><strong className="activation-code" aria-label="Activation code">{codes[request.id]}</strong><button type="button" className="icon-button table-action" aria-label={`Copy activation code for ${request.user.name}`} title="Copy code to share privately" onClick={() => copyCode(request)}><Copy size={15} /></button></span> : 'Hidden'}</td>
              <td className="table-actions"><button type="button" className="primary-button small" onClick={() => issueCode(request)}>{request.status === 'otp_issued' ? 'Reveal code' : 'Generate code'}</button><button type="button" className="ghost-button small" onClick={() => rejectRequest(request)}>Reject</button></td>
            </tr>)}
          </tbody></table></div>}
      <p className="field-help">Codes expire after five minutes. Share the displayed code privately with the staff member. It is never sent automatically or shown in their account.</p>
    </section>
  )
}
