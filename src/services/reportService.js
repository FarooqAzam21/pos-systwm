import api from './api'

const cleanParams = (params) => Object.fromEntries(
  Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
)

export const reportService = {
  async get(name, params = {}) {
    return (await api.get(`/reports/${name}`, { params: cleanParams(params) })).data
  },
  async getDashboard(params = {}) {
    return (await api.get('/reports/dashboard', { params: cleanParams(params) })).data
  },
  async closeDay(payload) {
    return (await api.post('/reports/daily-closing', payload)).data
  },
  async export(name, format, params = {}) {
    return (await api.get(`/reports/${name}/export.${format}`, {
      params: cleanParams(params),
      responseType: 'blob',
    })).data
  },
  async getAuditLogs(params = {}) {
    return (await api.get('/audit-logs', { params: cleanParams(params) })).data
  },
  async getFilterOptions() {
    const [customers, users, suppliers, categories, products, expenseCategories] = await Promise.all([
      api.get('/customers', { params: { limit: 200 } }),
      api.get('/users'),
      api.get('/suppliers'),
      api.get('/categories'),
      api.get('/products', { params: { limit: 200 } }),
      api.get('/expenses/categories'),
    ])
    return {
      customers: customers.data.items || customers.data,
      users: users.data,
      suppliers: suppliers.data.items || suppliers.data,
      categories: categories.data,
      products: products.data.items || products.data,
      expenseCategories: expenseCategories.data,
    }
  },
}
