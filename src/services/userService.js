import api from './api'

export const userService = {
  async list() {
    return (await api.get('/users')).data
  },
  async create(payload) {
    return (await api.post('/users', payload)).data
  },
  async update(id, payload) {
    return (await api.put(`/users/${id}`, payload)).data
  },
  async activationRequests() {
    return (await api.get('/users/activation-requests')).data
  },
  async generateActivationOtp(id) {
    return (await api.post(`/users/activation-requests/${id}/otp`)).data
  },
  async readActivationOtp(id) {
    return (await api.get(`/users/activation-requests/${id}/otp`)).data
  },
  async rejectActivation(id) {
    return api.delete(`/users/activation-requests/${id}`)
  },
  async resetPassword(id) {
    return (await api.post(`/users/${id}/password-reset`)).data
  },
  async revokeSessions(id) {
    return api.post(`/users/${id}/revoke-sessions`)
  },
}
