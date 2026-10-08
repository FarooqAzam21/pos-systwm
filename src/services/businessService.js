import api from './api'

export const businessService = {
  async get() {
    return (await api.get('/business')).data
  },
  async update(details) {
    return (await api.put('/business', details)).data
  },
}
