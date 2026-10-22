import api from './api'

// Render's free backend may need a while to wake after inactivity.
const AUTH_REQUEST_TIMEOUT = 65000

export const authService = {
  async register(details) {
    return (await api.post('/auth/register', details, { timeout: AUTH_REQUEST_TIMEOUT })).data
  },
  async login(credentials) {
    return (await api.post('/auth/login', credentials, { timeout: AUTH_REQUEST_TIMEOUT })).data
  },
  async me() {
    return (await api.get('/auth/me', { timeout: AUTH_REQUEST_TIMEOUT })).data
  },
  async updateMe(details) {
    return (await api.put('/auth/me', details)).data
  },
}
