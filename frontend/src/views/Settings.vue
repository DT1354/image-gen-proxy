<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import api from '../api'

const auth = useAuth()
const router = useRouter()

const email = ref(auth.user?.email || '')
const oldPassword = ref('')
const newPassword = ref('')
const error = ref('')
const success = ref('')

async function updateProfile() {
  error.value = ''
  success.value = ''
  try {
    await api.put('/api/auth/profile', {
      email: email.value || null,
      old_password: oldPassword.value || null,
      new_password: newPassword.value || null
    })
    success.value = '资料已更新'
    oldPassword.value = ''
    newPassword.value = ''
    await auth.fetchUser()
  } catch (e) {
    error.value = e.response?.data?.detail || '更新失败'
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="settings-page">
    <div class="page-header">
      <h1>设置</h1>
      <p>管理你的账号和偏好</p>
    </div>

    <div class="settings-grid">
      <!-- 个人资料 -->
      <div class="card section">
        <h2 class="section-title">个人资料</h2>
        <form @submit.prevent="updateProfile" class="form">
          <div class="form-group">
            <label>用户名</label>
            <input :value="auth.user?.username" disabled />
          </div>
          <div class="form-group">
            <label>邮箱</label>
            <input v-model="email" type="email" placeholder="可选" />
          </div>
          <div class="form-group">
            <label>当前密码</label>
            <input v-model="oldPassword" type="password" placeholder="修改密码时需要" />
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input v-model="newPassword" type="password" placeholder="留空则不修改" />
          </div>
          <div v-if="error" class="error-msg">{{ error }}</div>
          <div v-if="success" class="success-msg">{{ success }}</div>
          <button type="submit" class="btn primary">保存修改</button>
        </form>
      </div>

      <!-- 账号信息 -->
      <div class="card section">
        <h2 class="section-title">账号信息</h2>
        <div class="info-list">
          <div class="info-item">
            <span class="info-label">用户ID</span>
            <span class="info-value num">{{ auth.user?.id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">角色</span>
            <span :class="['tag', auth.user?.is_admin ? 'accent' : '']">
              {{ auth.user?.is_admin ? '管理员' : '普通用户' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">每日限额</span>
            <span class="info-value num">{{ auth.user?.daily_limit || 10 }} 次</span>
          </div>
        </div>

        <button v-if="auth.user?.is_admin" @click="router.push('/admin')" class="btn full">
          管理后台
        </button>
      </div>

      <!-- 退出登录 -->
      <div class="card section">
        <button @click="logout" class="btn danger full">退出登录</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 4px;
}

.page-header p {
  font-size: 13px;
  color: var(--t2);
  margin: 0;
}

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section {
  padding: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 20px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--t2);
}

.form-group input {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--t1);
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent);
}

.form-group input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-msg {
  font-size: 12px;
  color: var(--bad);
}

.success-msg {
  font-size: 12px;
  color: var(--good);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 13px;
  color: var(--t2);
}

.info-value {
  font-size: 13px;
  color: var(--t1);
}

.full {
  width: 100%;
  justify-content: center;
}

.danger {
  background: var(--bad-soft);
  border-color: var(--bad);
  color: var(--bad);
}

.danger:hover {
  background: var(--bad);
  color: white;
}
</style>
