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
}
