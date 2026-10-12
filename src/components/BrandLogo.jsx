import { useState } from 'react'

export const ORVION_LOGO_URL = 'https://www.theorvion.io/assets/logo.png'

export default function BrandLogo({ className = '', alt = 'The Orvion logo', src = ORVION_LOGO_URL }) {
  const [failed, setFailed] = useState(false)
  return <img
    className={className}
    src={failed ? '/orvion-mark.svg' : src}
    alt={alt}
    onError={() => setFailed(true)}
  />
}
