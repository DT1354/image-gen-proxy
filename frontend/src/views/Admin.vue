<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const users = ref([])
const loading = ref(true)

onMounted(async () => {
  await loadUsers()
})

async function loadUsers() {
  loading.value = true
  try {
    const res = await api.get('/api/admin/users')
    users.value = res.data.users
  } catch (e) {
    console.error('Failed to load users:', e)
  } finally {
    loading.value = false
  }
}

async function setLimit(userId, limit) {
  try {
    await api.put(`/api/admin/users/${userId}/limit?limit=${limit}`)
    await loadUsers()
  } catch (e) {
    console.error('Failed to set limit:', e)
  }
}

async function deleteUser(userId) {
  if (!confirm('确定要删除这个用户吗？')) return
  try {
    await api.delete(`/api/admin/users/${userId}`)
    await loadUsers()
  } catch (e) {
    console.error('Failed to delete user:', e)
  }
}
</script>

<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>管理后台</h1>
      <p>管理所有用户和系统设置</p>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="card section">
      <h2 class="section-title">用户列表</h2>
      
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>邮箱</th>
              <th>角色</th>
              <th>每日限额</th>
              <th>注册时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td class="num">{{ user.id }}</td>
              <td>{{ user.username }}</td>
              <td>{{ user.email || '-' }}</td>
              <td>
                <span :class="['tag', user.is_admin ? 'accent' : '']">
                  {{ user.is_admin ? '管理员' : '用户' }}
                </span>
              </td>
              <td>
                <input
                  type="number"
                  :value="user.daily_limit"
                  @change="setLimit(user.id, $event.target.value)"
                  class="limit-input"
                  min="1"
                  max="1000"
                />
              </td>
              <td>{{ new Date(user.created_at).toLocaleDateString() }}</td>
              <td>
                <button
                  v-if="!user.is_admin"
                  @click="deleteUser(user.id)"
                  class="btn small danger"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: 1200px;
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

.loading {
  text-align: center;
  padding: 48px;
  color: var(--t3);
}

.section {
  padding: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 20px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

th {
  font-weight: 600;
  color: var(--t2);
  background: var(--surface-2);
}

td {
  color: var(--t1);
}

tr:hover td {
  background: var(--surface-2);
}

.limit-input {
  width: 80px;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--t1);
  font-size: 13px;
}

.limit-input:focus {
  outline: none;
  border-color: var(--accent);
}

.small {
  padding: 4px 10px;
  font-size: 12px;
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
