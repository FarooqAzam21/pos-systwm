import { Package } from 'lucide-react'

export default function ComingSoon({ title }) {
  return <section className="coming-soon panel"><span className="coming-icon"><Package size={23} /></span><span className="eyebrow">WORKSPACE MODULE</span><h1>{title}</h1><p>This module is not part of the foundation release. Your business workspace is ready for it.</p><span className="coming-badge">Coming soon</span></section>
}
