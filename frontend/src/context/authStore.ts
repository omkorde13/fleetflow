import { create } from 'zustand'
import { authApi } from '@/services/api'

interface User {
  id: string
  email: string
  full_name: string
  role: 'CLIENT' | 'DRIVER' | 'ADMIN'
  avatar_url?: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: any) => Promise<void>
  logout: () => Promise<void>
  setUser: (user: User) => void
}

const getStoredUser = (): User | null => {
  const token = localStorage.getItem('access_token')
  const userStr = localStorage.getItem('user')
  if (!token || !userStr) return null
  try {
    return JSON.parse(userStr)
  } catch {
    localStorage.clear()
    return null
  }
}

const storedUser = getStoredUser()

export const useAuthStore = create<AuthState>((set, get) => ({
  user: storedUser,
  isAuthenticated: !!storedUser,
  isLoading: false,

  login: async (email, password) => {
    set({ isLoading: true })
    try {
      const { data } = await authApi.login({ email, password })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      // Decode basic user info from response
      const user: User = {
        id: data.user_id,
        email,
        full_name: '',
        role: data.role,
      }
      localStorage.setItem('user', JSON.stringify(user))
      set({ user, isAuthenticated: true })
    } finally {
      set({ isLoading: false })
    }
  },

  register: async (data) => {
    set({ isLoading: true })
    try {
      const { data: res } = await authApi.register(data)
      localStorage.setItem('access_token', res.access_token)
      localStorage.setItem('refresh_token', res.refresh_token)
      const user: User = {
        id: res.user_id,
        email: data.email,
        full_name: data.full_name,
        role: res.role,
      }
      localStorage.setItem('user', JSON.stringify(user))
      set({ user, isAuthenticated: true })
    } finally {
      set({ isLoading: false })
    }
  },

  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token') || ''
    try {
      await authApi.logout(refreshToken)
    } catch {}
    localStorage.clear()
    set({ user: null, isAuthenticated: false })
  },

  setUser: (user) => {
    localStorage.setItem('user', JSON.stringify(user))
    set({ user })
  },
}))
