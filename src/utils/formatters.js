export const CURRENCY_KEY = 'pos_business_currency'

export function formatCurrency(value, currency = localStorage.getItem(CURRENCY_KEY) || 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value) || 0)
}
