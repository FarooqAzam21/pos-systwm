import BrandLogo from './BrandLogo'

function formatDateTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value || '')
  return {
    date: date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' }),
    time: date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
  }
}

export default function ThermalReceipt({ sale, business, cashierName, amount }) {
  const { date, time } = formatDateTime(sale.sale_date)
  const payments = sale.payments || []
  const paymentMethods = [...new Set(payments.map((payment) => payment.payment_method).filter(Boolean))]

  return (
    <article className="thermal-receipt" aria-label={`Thermal receipt ${sale.invoice_number}`}>
      <header className="thermal-business">
        {business?.logo && <BrandLogo src={business.logo} className="thermal-logo" />}
        <h2>{business?.business_name || 'Business'}</h2>
        {[business?.address, business?.city].filter(Boolean).length > 0 && <p>{[business.address, business.city].filter(Boolean).join(', ')}</p>}
        {business?.phone && <p>{business.phone}</p>}
        {business?.email && <p>{business.email}</p>}
        {business?.tax_number && <p>Tax no: {business.tax_number}</p>}
      </header>

      <div className="thermal-rule" />
      <section className="thermal-meta" aria-label="Transaction details">
        <div><span>Receipt</span><strong>{sale.invoice_number}</strong></div>
        <div><span>Date</span><strong>{date}</strong></div>
        <div><span>Time</span><strong>{time}</strong></div>
        <div><span>Cashier</span><strong>{sale.cashier_name || cashierName || '—'}</strong></div>
        {(sale.customer_name || sale.customer_phone) && <div><span>Customer</span><strong>{sale.customer_name || '—'}{sale.customer_phone ? ` · ${sale.customer_phone}` : ''}</strong></div>}
      </section>

      <div className="thermal-rule" />
      <div className="thermal-items" role="table" aria-label="Purchased items">
        <div className="thermal-item thermal-item-heading" role="row"><span role="columnheader">Item</span><span role="columnheader">Qty</span><span role="columnheader">Price</span><span role="columnheader">Total</span></div>
        {sale.items.map((item) => (
          <div className="thermal-item" role="row" key={item.id}>
            <span className="thermal-product-name" role="cell">{item.product_name}{Number(item.returned_quantity) > 0 && <small>Returned {item.returned_quantity}</small>}</span>
            <span role="cell">{item.quantity}</span>
            <span role="cell">{amount(item.unit_price)}</span>
            <span role="cell">{amount(item.line_total)}</span>
          </div>
        ))}
      </div>

      <div className="thermal-rule" />
      <dl className="thermal-totals">
        <div><dt>Subtotal</dt><dd>{amount(sale.subtotal)}</dd></div>
        {Number(sale.discount) !== 0 && <div><dt>Discount</dt><dd>−{amount(sale.discount)}</dd></div>}
        {Number(sale.tax) !== 0 && <div><dt>Tax</dt><dd>{amount(sale.tax)}</dd></div>}
        <div className="thermal-grand-total"><dt>Total{sale.returns?.length ? ' (net of returns)' : ''}</dt><dd>{amount(sale.total_amount)}</dd></div>
      </dl>

      <div className="thermal-rule" />
      <section className="thermal-payment" aria-label="Payments">
        {paymentMethods.length > 0 && <div><span>Payment</span><strong>{paymentMethods.map((method) => method.replaceAll('_', ' ')).join(', ')}</strong></div>}
        {payments.map((payment) => <div key={payment.id}><span>Received{payments.length > 1 && payment.payment_method ? ` · ${payment.payment_method.replaceAll('_', ' ')}` : ''}</span><strong>{amount(payment.amount)}</strong></div>)}
        <div><span>Paid to date</span><strong>{amount(sale.paid_amount)}</strong></div>
        {Number(sale.outstanding_amount) > 0 && <div><span>Balance due</span><strong>{amount(sale.outstanding_amount)}</strong></div>}
      </section>

      <div className="thermal-rule" />
      <footer className="thermal-footer">
        {business?.invoice_footer && <p>{business.invoice_footer}</p>}
        <p>Thank you for your business!</p>
        <small>Powered by The Orvion</small>
      </footer>
    </article>
  )
}
