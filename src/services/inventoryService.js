import api from './api'

const normalizeParams = (params = {}) => Object.fromEntries(
  Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
)

export const inventoryService = {
  async getSummary() {
    const { data } = await api.get('/inventory')
    return data
  },
  async getLowStock() {
    const { data } = await api.get('/inventory/low-stock')
    return data
  },
  async getOutOfStock() {
    const { data } = await api.get('/inventory/out-of-stock')
    return data
  },
  async getMovements(productId) {
    const { data } = await api.get(`/inventory/${productId}/movements`)
    return data
  },
  async createOpeningStock(productId, details) {
    const { data } = await api.post(`/inventory/${productId}/opening-stock`, details)
    return data
  },
  async adjustStock(productId, details) {
    const { data } = await api.post(`/inventory/${productId}/adjust`, details)
    return data
  },

  async getCategories() {
    const { data } = await api.get('/categories')
    return data
  },
  async createCategory(details) {
    const { data } = await api.post('/categories', details)
    return data
  },
  async updateCategory(id, details) {
    const { data } = await api.put(`/categories/${id}`, details)
    return data
  },
  async deleteCategory(id) {
    const { data } = await api.delete(`/categories/${id}`)
    return data
  },

  async getSuppliers() {
    const { data } = await api.get('/suppliers')
    return data
  },
  async createSupplier(details) {
    const { data } = await api.post('/suppliers', details)
    return data
  },
  async updateSupplier(id, details) {
    const { data } = await api.put(`/suppliers/${id}`, details)
    return data
  },
  async deleteSupplier(id) {
    const { data } = await api.delete(`/suppliers/${id}`)
    return data
  },

  async getProducts(params = {}) {
    const { data } = await api.get('/products', { params: normalizeParams(params) })
    return data
  },
  async getProduct(id) {
    const { data } = await api.get(`/products/${id}`)
    return data
  },
  async createProduct(details) {
    const { data } = await api.post('/products', details)
    return data
  },
  async updateProduct(id, details) {
    const { data } = await api.put(`/products/${id}`, details)
    return data
  },
  async deleteProduct(id) {
    const { data } = await api.delete(`/products/${id}`)
    return data
  },
}
