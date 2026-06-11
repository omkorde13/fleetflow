import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — attach token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor — auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')

      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          original.headers!.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api

// ── Typed API helpers ──────────────────────────────────────

export const authApi = {
  register: (data: any) => api.post('/auth/register', data),
  login: (data: any) => api.post('/auth/login', data),
  logout: (refreshToken: string) => api.post('/auth/logout', { refresh_token: refreshToken }),
  forgotPassword: (email: string) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token: string, newPassword: string) =>
    api.post('/auth/reset-password', { token, new_password: newPassword }),
  googleLogin: () => { window.location.href = `${API_BASE}/api/v1/auth/google/login` },
}

export const deliveryApi = {
  create: (data: any) => api.post('/deliveries', data),
  list: (params?: any) => api.get('/deliveries', { params }),
  get: (id: string) => api.get(`/deliveries/${id}`),
  cancel: (id: string, reason: string) => api.post(`/deliveries/${id}/cancel`, { reason }),
  accept: (id: string) => api.post(`/deliveries/${id}/accept`),
  pickup: (id: string, otp: string) => api.post(`/deliveries/${id}/pickup`, { otp }),
  complete: (id: string, otp: string) => api.post(`/deliveries/${id}/complete`, { otp }),
  estimateFare: (data: any) => api.post('/users/pricing/estimate', data),
  assign: (id: string, driverId: string) =>
    api.post(`/deliveries/${id}/assign`, { driver_id: driverId }),
  rate: (id: string, rating: number, comment?: string) =>
    api.post(`/deliveries/${id}/rate`, { rating, comment }),
}

export const paymentApi = {
  createOrder: (deliveryId: string) =>
    api.post('/payments/orders', { delivery_id: deliveryId }),
  payCash: (deliveryId: string) =>
    api.post('/payments/cod', { delivery_id: deliveryId }),
  confirmCash: (paymentId: string) =>
    api.post(`/payments/${paymentId}/confirm-cash`),
  getByDelivery: (deliveryId: string) =>
    api.get(`/payments/by-delivery/${deliveryId}`),
  verify: (data: any) => api.post('/payments/verify', data),
  history: () => api.get('/payments/history'),
  refund: (paymentId: string) => api.post(`/payments/${paymentId}/refund`),
}

export const offerApi = {
  listActive: () => api.get('/offers'),
  validate: (code: string) => api.get(`/offers/validate/${code}`),
  create: (data: any) => api.post('/offers', data),
  disable: (id: string) => api.patch(`/offers/${id}/disable`),
}

export const driverApi = {
  createProfile: (data: any) => api.post('/drivers/profile', data),
  getProfile: () => api.get('/drivers/profile/me'),
  updateStatus: (status: string) =>
    api.patch('/drivers/status', null, { params: { status } }),
  getNearby: (lat: number, lng: number, radius?: number) =>
    api.get('/drivers/nearby', { params: { lat, lng, radius_km: radius || 10 } }),
}

export const userApi = {
  me: () => api.get('/users/me'),
  updateMe: (data: any) => api.put('/users/me', data),
  notifications: (unreadOnly?: boolean) =>
    api.get('/users/me/notifications', { params: { unread_only: unreadOnly } }),
  markAllRead: () => api.post('/users/me/notifications/read-all'),
  markRead: (id: string) => api.post(`/users/me/notifications/${id}/read`),
}

export const adminApi = {
  dashboard: () => api.get('/admin/dashboard'),
  revenueReport: (period: string) =>
    api.get('/admin/reports/revenue', { params: { period } }),
  listUsers: (params?: any) => api.get('/admin/users', { params }),
  updateUserStatus: (id: string, isActive: boolean) =>
    api.patch(`/admin/users/${id}/status`, null, { params: { is_active: isActive } }),
  listDrivers: (params?: any) => api.get('/admin/drivers', { params }),
  verifyDriver: (id: string) => api.patch(`/admin/drivers/${id}/verify`),
  suspendDriver: (id: string) => api.patch(`/admin/drivers/${id}/suspend`),
}
