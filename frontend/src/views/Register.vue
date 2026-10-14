<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')

async function handleRegister() {
  error.value = ''
  if (password.value !== confirmPassword.value) {
    error.value = '两次密码不一致'
    return
  }
  try {
    await auth.register(username.value, email.value || null, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败'
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card card">
      <div class="auth-header">
        <div class="auth-logo">
          <span class="logo-ic">🎨</span>
        </div>
        <h1>创建账号</h1>
        <p>注册后即可使用 AI 图像生成</p>
      </div>

      <form @submit.prevent="handleRegister" class="auth-form">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" required placeholder="3-20个字符" />
        </div>
        <div class="form-group">
          <label>邮箱（可选）</label>
          <input v-model="email" type="email" placeholder="用于找回密码" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" required placeholder="至少6位" />
        </div>
        <div class="form-group">
          <label>确认密码</label>
          <input v-model="confirmPassword" type="password" required placeholder="再次输入密码" />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button type="submit" class="btn primary full" :disabled="auth.loading">
          {{ auth.loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <div class="auth-footer">
        已有账号？<router-link to="/login">登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.auth-card {
  width: 100%;
  max-width: 380px;
  padding: 40px 32px;
}
.auth-header {
  text-align: center;
  margin-bottom: 32px;
}
.auth-logo {
  margin-bottom: 16px;
}
.logo-ic {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--accent);
  color: var(--on-accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}
.auth-header h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 8px;
}
.auth-header p {
  font-size: 13px;
  color: var(--t2);
  margin: 0;
}
.auth-form {
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
  transition: all var(--dur) var(--ease);
}
.form-group input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.error-msg {
  font-size: 12px;
  color: var(--bad);
  text-align: center;
}
.full {
  width: 100%;
  justify-content: center;
}
.auth-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: var(--t2);
}
</style>
