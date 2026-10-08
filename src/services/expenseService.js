import api from './api'

const cleanParams = (params) => Object.fromEntries(
  Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
)

export const expenseService = {
  async getCategories() {
    return (await api.get('/expenses/categories')).data
  },
  async createCategory(payload) {
    return (await api.post('/expenses/categories', payload)).data
  },
  async getExpenses(params = {}) {
    return (await api.get('/expenses', { params: cleanParams(params) })).data
  },
  async createExpense(payload) {
    return (await api.post('/expenses', payload)).data
  },
  async updateExpense(id, payload) {
    return (await api.put(`/expenses/${id}`, payload)).data
  },
  async deleteExpense(id) {
    return api.delete(`/expenses/${id}`)
  },
}
