<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const images = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/api/history?limit=50')
    images.value = res.data.images
  } catch (e) {
    console.error('Failed to load history:', e)
  } finally {
    loading.value = false
  }
})

async function downloadImage(url) {
  try {
    const response = await api.get(`/api/download?url=${encodeURIComponent(url)}`, {
      responseType: 'blob'
    })
    const downloadUrl = window.URL.createObjectURL(new Blob([response.data]))
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = 'image.png'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(downloadUrl)
  } catch (e) {
    console.error('Download failed:', e)
  }
}
</script>

<template>
  <div class="history-page">
    <div class="page-header">
      <h1>生成历史</h1>
      <p>查看你之前生成的所有图片</p>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="!images.length" class="empty">
      <div class="empty-icon">📭</div>
      <p>暂无生成记录</p>
    </div>

    <div v-else class="grid">
      <div v-for="img in images" :key="img.id" class="grid-item card">
        <img :src="`${API_BASE}/images/${img.filename}`" />
        <div class="item-info">
          <div class="item-prompt">{{ img.prompt || '无提示词' }}</div>
          <div class="item-meta">
            <span>{{ img.model }}</span>
            <span>{{ img.size }}</span>
            <span>{{ new Date(img.created_at).toLocaleDateString() }}</span>
          </div>
        </div>
        <div class="item-actions">
          <button @click="downloadImage(`/images/${img.filename}`)" class="btn">⬇️ 下载</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-page {
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

.loading, .empty {
  text-align: center;
  padding: 64px 20px;
  color: var(--t3);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.grid-item {
  overflow: hidden;
}

.grid-item img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
}

.item-info {
  padding: 12px;
}

.item-prompt {
  font-size: 13px;
  color: var(--t1);
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--t3);
}

.item-meta span {
  padding: 2px 6px;
  background: var(--surface-2);
  border-radius: 4px;
}

.item-actions {
  padding: 0 12px 12px;
}

.item-actions .btn {
  width: 100%;
  justify-content: center;
}
</style>
