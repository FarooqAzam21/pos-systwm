import api from './api'

const cleanParams = (params) => Object.fromEntries(
  Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
)

export const commerceService = {
  async getCustomers(params = {}) {
    return (await api.get('/customers', { params: cleanParams(params) })).data
  },
  async getCustomer(id) {
    return (await api.get(`/customers/${id}`)).data
  },
  async createCustomer(payload) {
    return (await api.post('/customers', payload)).data
  },
  async updateCustomer(id, payload) {
    return (await api.put(`/customers/${id}`, payload)).data
  },
  async deactivateCustomer(id) {
    return (await api.delete(`/customers/${id}`)).data
  },
  async receiveCustomerPayment(payload) {
    return (await api.post('/payments/customer', payload)).data
  },
  async getPurchases(params = {}) {
    return (await api.get('/purchases', { params: cleanParams(params) })).data
  },
  async getPurchase(id) {
    return (await api.get(`/purchases/${id}`)).data
  },
  async paySupplier(payload) {
    return (await api.post('/payments/supplier', payload)).data
  },
  async createPurchase(payload) {
    return (await api.post('/purchases', payload)).data
  },
  async getPurchaseOrders(params = {}) {
    return (await api.get('/purchase-orders', { params: cleanParams(params) })).data
  },
  async createPurchaseOrder(payload) {
    return (await api.post('/purchase-orders', payload)).data
  },
  async updatePurchaseOrder(id, status) {
    return (await api.patch(`/purchase-orders/${id}`, { status })).data
  },
  async receivePurchaseOrder(id, payload) {
    return (await api.post(`/purchase-orders/${id}/receive`, payload)).data
  },
  async getSales(params = {}) {
    return (await api.get('/sales', { params: cleanParams(params) })).data
  },
  async getSale(id) {
    return (await api.get(`/sales/${id}`)).data
  },
  async downloadInvoicePdf(id) {
    return (await api.get(`/sales/${id}/invoice/pdf`, { responseType: 'blob' })).data
  },
  async getReturns(params = {}) {
    return (await api.get('/returns', { params: cleanParams(params) })).data
  },
  async createSale(payload) {
    return (await api.post('/sales', payload)).data
  },
  async returnSale(id, payload) {
    return (await api.post(`/sales/${id}/returns`, payload)).data
  },
  async getPayments(params = {}) {
    return (await api.get('/payments', { params: cleanParams(params) })).data
  },
  async getDashboard(params = {}) {
    return (await api.get('/dashboard/overview', { params: cleanParams(params) })).data
  },
}
