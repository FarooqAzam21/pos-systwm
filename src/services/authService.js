import api from './api'

export const authService = {
  async register(details) {
    return (await api.post('/auth/register', details)).data
  },
  async login(credentials) {
    return (await api.post('/auth/login', credentials)).data
  },
  async me() {
    return (await api.get('/auth/me')).data
  },
  async updateMe(details) {
    return (await api.put('/auth/me', details)).data
  },
}
