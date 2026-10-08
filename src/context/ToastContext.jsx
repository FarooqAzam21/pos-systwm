import { useCallback, useMemo, useRef, useState } from 'react'
import { ToastContext } from './ToastContextValue'
import { AlertCircle, CheckCircle2, X } from 'lucide-react'

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const timer = useRef(null)
  const notify = useCallback((message, type = 'success') => {
    setToast({ message, type })
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setToast(null), 3600)
  }, [])
  const value = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast && (
        <div className={`toast ${toast.type}`} role="status">
          {toast.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          <span>{toast.message}</span>
          <button aria-label="Dismiss notification" onClick={() => setToast(null)}><X size={16} /></button>
        </div>
      )}
    </ToastContext.Provider>
  )
}
