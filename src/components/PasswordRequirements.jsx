import { Check, Circle } from 'lucide-react'

export const passwordRequirements = (password, minLength = 10) => [
  { label: `At least ${minLength} characters`, met: password.length >= minLength },
  { label: 'One uppercase letter', met: /[A-Z]/.test(password) },
  { label: 'One number', met: /[0-9]/.test(password) },
  { label: 'One special character', met: /[^A-Za-z0-9\s]/.test(password) },
]

export const isStrongPassword = (password, minLength = 10) =>
  passwordRequirements(password, minLength).every(({ met }) => met)

export default function PasswordRequirements({ password, minLength = 10, className = '' }) {
  return (
    <ul className={`password-requirements ${className}`.trim()} aria-label="Password requirements" aria-live="polite">
      {passwordRequirements(password, minLength).map(({ label, met }) => (
        <li className={met ? 'met' : ''} key={label}>
          {met ? <Check size={13} aria-hidden="true" /> : <Circle size={13} aria-hidden="true" />}
          <span>{label}</span>
        </li>
      ))}
    </ul>
  )
}
