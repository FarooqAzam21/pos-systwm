import BrandLogo from './BrandLogo'

function formatDateTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return { date: String(value || ''), time: '' }
  return {
    date: date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' }),
    time: date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
  }
}

export default function ThermalPaymentReceipt({ sale, payment, business, cashierName, amount }) {
  const { date, time } = formatDateTime(payment.payment_date)
  return (
    <article className="thermal-receipt thermal-payment-receipt" aria-label={`Payment receipt for ${sale.invoice_number}`}>
      <header className="thermal-business">
        {business?.logo && <BrandLogo src={business.logo} className="thermal-logo" />}
        <h2>{business?.business_name || 'Business'}</h2>
        {[business?.address, business?.city].filter(Boolean).length > 0 && <p>{[business.address, business.city].filter(Boolean).join(', ')}</p>}
        {business?.phone && <p>{business.phone}</p>}
        {business?.email && <p>{business.email}</p>}
      </header>
      <div className="thermal-rule" />
      <div className="thermal-receipt-kind">PAYMENT RECEIPT</div>
      <section className="thermal-meta" aria-label="Payment details">
        <div><span>Invoice</span><strong>{sale.invoice_number}</strong></div>
        <div><span>Date</span><strong>{date}{time ? ` · ${time}` : ''}</strong></div>
        <div><span>Payment ref.</span><strong>{String(payment.id).slice(-8).toUpperCase()}</strong></div>
        <div><span>Cashier</span><strong>{cashierName || sale.cashier_name || '—'}</strong></div>
        {sale.customer_name && <div><span>Customer</span><strong>{sale.customer_name}</strong></div>}
      </section>
      <div className="thermal-rule" />
      <section className="thermal-payment" aria-label="Payment summary">
        <div><span>Payment method</span><strong>{String(payment.payment_method || '').replaceAll('_', ' ')}</strong></div>
        {payment.reference_number && <div><span>Reference</span><strong>{payment.reference_number}</strong></div>}
        <div className="thermal-payment-received"><span>Received now</span><strong>{amount(payment.amount)}</strong></div>
        <div><span>Invoice total</span><strong>{amount(sale.total_amount)}</strong></div>
        <div><span>Total paid</span><strong>{amount(sale.paid_amount)}</strong></div>
        <div><span>Balance due</span><strong>{amount(sale.outstanding_amount)}</strong></div>
      </section>
      <div className="thermal-rule" />
      <footer className="thermal-footer">
        {business?.invoice_footer && <p>{business.invoice_footer}</p>}
        <p>Thank you for your payment!</p>
        <small>Powered by The Orvion</small>
      </footer>
    </article>
  )
}
