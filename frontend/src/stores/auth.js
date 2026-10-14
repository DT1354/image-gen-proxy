import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuth = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_admin)

  async function login(username, password) {
    loading.value = true
    try {
      const res = await api.post('/api/auth/login', { username, password })
      token.value = res.data.token
      user.value = res.data.user
      localStorage.setItem('token', token.value)
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function register(username, email, password) {
    loading.value = true
    try {
      const res = await api.post('/api/auth/register', { username, email, password })
      token.value = res.data.token
      user.value = res.data.user
      localStorage.setItem('token', token.value)
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await api.get('/api/auth/me')
      user.value = res.data
    } catch (e) {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    loading,
    isLoggedIn,
    isAdmin,
    login,
    register,
    fetchUser,
    logout
  }
})
