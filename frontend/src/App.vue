<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from './stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuth()

const theme = ref(localStorage.getItem('theme') || 'midnight')

onMounted(async () => {
  if (auth.isLoggedIn) {
    await auth.fetchUser()
  }
  applyTheme()
})

function applyTheme() {
  document.documentElement.setAttribute('data-theme', theme.value)
  localStorage.setItem('theme', theme.value)
}

function setTheme(t) {
  theme.value = t
  applyTheme()
}

const NAV = computed(() => {
  const items = [
    { to: '/', icon: '🎨', label: '工作台' },
    { to: '/history', icon: '📋', label: '历史记录' },
    { to: '/settings', icon: '⚙️', label: '设置' },
  ]
  if (auth.isAdmin) {
    items.push({ to: '/admin', icon: '👥', label: '管理后台' })
  }
  return items
})

const hello = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <!-- 未登录显示登录页 -->
  <router-view v-if="!auth.isLoggedIn && route.path !== '/register'" />
  <router-view v-else-if="route.path === '/register'" />

  <!-- 已登录显示主界面 -->
  <template v-else>
    <div class="shell">
      <aside class="side">
        <div class="logo">
          <span class="logo-ic">🎨</span>
          <span class="logo-tx">AI 工作台</span>
        </div>

        <nav class="nav">
          <router-link
            v-for="n in NAV"
            :key="n.to"
            :to="n.to"
            class="nav-item"
            :class="{ on: route.path === n.to }"
          >
            <span class="nav-icon">{{ n.icon }}</span>
            <span>{{ n.label }}</span>
          </router-link>
        </nav>

        <div class="side-bottom">
          <div class="user">
            <span class="uav">{{ auth.user?.username?.slice(0, 1) || '?' }}</span>
            <div class="umeta">
              <div class="uname">{{ auth.user?.username }}</div>
              <div class="urole">{{ auth.user?.is_admin ? '管理员' : '用户' }}</div>
            </div>
          </div>
          <button @click="logout" class="logout-btn">退出</button>
        </div>
      </aside>

      <div class="main">
        <header class="top">
          <div class="hello">
            <div class="h1">{{ hello }}，{{ auth.user?.username }}</div>
            <div class="h2">
              {{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }) }}
            </div>
          </div>
          <div class="top-right">
            <div class="theme-dots">
              <button
                v-for="t in ['midnight', 'dawn', 'mono', 'forest']"
                :key="t"
                :class="['theme-dot', t, { active: theme === t }]"
                @click="setTheme(t)"
                :title="t"
              />
            </div>
          </div>
        </header>

        <main class="content">
          <router-view />
        </main>
      </div>
    </div>

    <!-- 移动端底部导航 -->
    <nav class="tabbar">
      <router-link
        v-for="n in NAV"
        :key="n.to"
        :to="n.to"
        class="tab"
        :class="{ on: route.path === n.to }"
      >
        <span class="tab-icon">{{ n.icon }}</span>
        <span>{{ n.label.split('').slice(0, 2).join('') }}</span>
      </router-link>
    </nav>
  </template>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100dvh;
  position: relative;
  z-index: 1;
}

/* 侧栏 */
.side {
  width: 200px;
  flex-shrink: 0;
  padding: 20px 12px;
  border-right: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 55%, transparent);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 0;
  height: 100dvh;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px;
}

.logo-ic {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--accent);
  color: var(--on-accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.logo-tx {
  font-size: 15px;
  font-weight: 700;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--t2);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  transition: all var(--dur) var(--ease);
  text-decoration: none;
}

.nav-item:hover {
  color: var(--t1);
  background: var(--surface-2);
}

.nav-item.on {
  color: var(--t1);
  background: var(--surface-3);
  font-weight: 600;
}

.nav-icon {
  font-size: 14px;
}

.side-bottom {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.user {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.uav {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
}

.uname {
  font-size: 12px;
  font-weight: 600;
}

.urole {
  font-size: 11px;
  color: var(--t3);
}

.logout-btn {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--t2);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--dur) var(--ease);
}

.logout-btn:hover {
  border-color: var(--bad);
  color: var(--bad);
}

/* 主区 */
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 18px 28px 14px;
  position: sticky;
  top: 0;
  z-index: 20;
  background: color-mix(in srgb, var(--bg) 78%, transparent);
  backdrop-filter: blur(12px);
}

.h1 {
  font-size: 17px;
  font-weight: 700;
}

.h2 {
  font-size: 11.5px;
  color: var(--t3);
  margin-top: 2px;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.theme-dots {
  display: flex;
  gap: 6px;
}

.theme-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--border);
  cursor: pointer;
  transition: all var(--dur) var(--ease);
}

.theme-dot.midnight { background: #0A0F1E; }
.theme-dot.dawn { background: #F5F2EB; }
.theme-dot.mono { background: #FAFAF7; }
.theme-dot.forest { background: #0A110E; }

.theme-dot.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
}

.content {
  padding: 10px 28px 40px;
  flex: 1;
}

/* 移动端 */
.tabbar {
  display: none;
}

@media (max-width: 860px) {
  .side {
    display: none;
  }
  
  .top {
    padding: 14px 16px 10px;
  }
  
  .content {
    padding: 6px 14px 92px;
  }
  
  .tabbar {
    display: flex;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 30;
    background: color-mix(in srgb, var(--surface) 88%, transparent);
    backdrop-filter: blur(14px);
    border-top: 1px solid var(--border);
    padding: 6px 8px calc(8px + env(safe-area-inset-bottom));
  }
  
  .tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    font-size: 10px;
    color: var(--t3);
    padding: 5px 0;
    border-radius: 10px;
    text-decoration: none;
    transition: color var(--dur) var(--ease);
  }
  
  .tab.on {
    color: var(--accent);
    font-weight: 600;
  }
  
  .tab-icon {
    font-size: 18px;
  }
}
</style>
