import axios from 'axios'

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim()
const productionApiUrl = 'https://theorvion-pos-syst3m.onrender.com'
const localApiUrl = 'http://localhost:8000'
const configuredLocalhost = configuredApiUrl && /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\/?$/i.test(configuredApiUrl)
const apiBaseUrl = (import.meta.env.PROD && (!configuredApiUrl || configuredLocalhost)
  ? productionApiUrl
  : configuredApiUrl || localApiUrl).replace(/\/+$/, '')

const api = axios.create({
  baseURL: apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

let accessToken = null

export function setAccessToken(token) {
  accessToken = token
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || ''
    if (error.response?.status === 401 && !requestUrl.startsWith('/auth/login') && !requestUrl.startsWith('/auth/register')) {
      setAccessToken(null)
      localStorage.removeItem('pos_access_token')
      window.dispatchEvent(new Event('auth:expired'))
    }
    return Promise.reject(error)
  },
)

export function getApiErrorMessage(error) {
  const status = error.response?.status
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => `${item.loc?.at(-1) || 'Field'}: ${item.msg}`).join('. ')
  if (typeof detail === 'string') return detail
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to do that.'
  if (status === 404) return 'The requested information could not be found.'
  if (status === 422) return 'Please review the information and try again.'
  if (status >= 500) return 'The service is temporarily unavailable. Please try again.'
  if (error.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
  if (!error.response) return 'Could not reach the server. Check your connection and try again.'
  return 'Something went wrong. Please try again.'
}

export default api
