<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../stores/auth'
import api from '../api'

const auth = useAuth()

const mode = ref('text2img')
const prompt = ref('')
const referenceImage = ref(null)
const referenceImagePreview = ref(null)
const fileInput = ref(null)
const size = ref('1:1')
const resolution = ref('1k')
const count = ref(1)
const loading = ref(false)
const images = ref([])
const error = ref(null)
const fullSizeImage = ref(null)
const models = ref([])
const sizes = ref([
  { value: 'auto', label: '自动' },
  { value: '1:1', label: '1:1 正方形' },
  { value: '4:3', label: '4:3 横版' },
  { value: '3:4', label: '3:4 竖版' },
  { value: '16:9', label: '16:9 宽屏' },
  { value: '9:16', label: '9:16 竖屏' },
])
const resolutions = ref([
  { value: '1k', label: '1K 标准' },
  { value: '2k', label: '2K 高清' },
  { value: '4k', label: '4K 超高清' },
])

onMounted(async () => {
  await auth.fetchUser()
  try {
    const res = await api.get('/api/models')
    models.value = res.data.models
  } catch (e) {
    console.error('Failed to fetch models:', e)
  }
})

function triggerFileInput() {
  fileInput.value.click()
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) processFile(file)
}

function handleDrop(event) {
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) processFile(file)
}

function processFile(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    referenceImage.value = e.target.result
    referenceImagePreview.value = e.target.result
  }
  reader.readAsDataURL(file)
}

function clearReferenceImage() {
  referenceImage.value = null
  referenceImagePreview.value = null
  fileInput.value.value = ''
}

async function generate() {
  if (!prompt.value.trim() || loading.value) return

  loading.value = true
  error.value = null
  images.value = []

  try {
    let response
    if (mode.value === 'text2img') {
      response = await api.post('/api/generate/text', {
        prompt: prompt.value,
        n: count.value,
        size: size.value,
        resolution: resolution.value,
        reference_images: referenceImage.value ? [referenceImage.value] : null
      })
    } else {
      response = await api.post('/api/generate/image', {
        prompt: prompt.value,
        image: referenceImage.value,
        n: count.value,
        size: size.value,
        resolution: resolution.value
      })
    }

    if (response.data.success) {
      images.value = response.data.images
    } else {
      error.value = response.data.error || '生成失败，请重试'
    }
  } catch (err) {
    if (err.response?.status === 429) {
      error.value = '今日生成次数已用完，请明天再试'
    } else {
      error.value = err.response?.data?.detail || '生成失败，请重试'
    }
  } finally {
    loading.value = false
  }
}

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
    alert('下载失败，请重试')
  }
}

function openFullSize(url) {
  fullSizeImage.value = url
}
</script>

<template>
  <div class="workbench">
    <div class="workbench-main">
      <!-- 模型选择 -->
      <div class="card section">
        <h2 class="section-title">选择模型</h2>
        <div class="model-grid">
          <button
            v-for="model in models"
            :key="model.id"
            @click="selectedModel = model.id"
            :class="['model-card', { active: selectedModel === model.id }]"
          >
            <div class="model-name">{{ model.name }}</div>
            <div class="model-desc">{{ model.description.split('，')[0] }}</div>
          </button>
        </div>
      </div>

      <!-- 模式切换 -->
      <div class="card section">
        <div class="pill-tabs">
          <button :class="{ on: mode === 'text2img' }" @click="mode = 'text2img'">✏️ 文生图</button>
          <button :class="{ on: mode === 'img2img' }" @click="mode = 'img2img'">🖼️ 图生图</button>
        </div>

        <!-- 提示词输入 -->
        <div class="prompt-area">
          <label>提示词</label>
          <textarea
            v-model="prompt"
            rows="4"
            placeholder="描述你想要生成的图像..."
          ></textarea>
          <div class="prompt-footer">{{ prompt.length }} / 4000</div>
        </div>

        <!-- 参考图片（图生图模式） -->
        <div v-if="mode === 'img2img'" class="upload-area">
          <label>参考图片</label>
          <div
            @click="triggerFileInput"
            @dragover.prevent
            @drop.prevent="handleDrop"
            class="upload-box"
          >
            <div v-if="!referenceImagePreview" class="upload-placeholder">
              <div class="upload-icon">📷</div>
              <p>点击或拖拽上传图片</p>
              <p class="upload-hint">支持 JPG, PNG, WebP</p>
            </div>
            <div v-else class="upload-preview">
              <img :src="referenceImagePreview" />
              <button @click.stop="clearReferenceImage" class="upload-remove">✕</button>
            </div>
          </div>
          <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleFileSelect" />
        </div>

        <!-- 设置 -->
        <div class="settings-grid">
          <div class="form-group">
            <label>尺寸</label>
            <select v-model="size">
              <option v-for="s in sizes" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>分辨率</label>
            <select v-model="resolution">
              <option v-for="r in resolutions" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>数量</label>
            <select v-model="count">
              <option v-for="n in 4" :key="n" :value="n">{{ n }} 张</option>
            </select>
          </div>
        </div>

        <!-- 生成按钮 -->
        <button @click="generate" :disabled="loading || !prompt.trim()" class="btn primary full">
          {{ loading ? '生成中...' : '✨ 开始生成' }}
        </button>
      </div>
    </div>

    <!-- 结果面板 -->
    <div class="workbench-side">
      <div class="card section">
        <h2 class="section-title">生成结果</h2>
        
        <div v-if="!images.length && !loading" class="empty-state">
          <div class="empty-icon">🎨</div>
          <p>输入提示词开始创作</p>
        </div>

        <div v-if="loading" class="loading-state">
          <div class="loading-skeleton"></div>
          <p>正在生成图像...</p>
        </div>

        <div v-if="images.length" class="results">
          <div v-for="(img, index) in images" :key="index" class="result-item">
            <img :src="img" @click="openFullSize(img)" />
            <div class="result-actions">
              <button @click="downloadImage(img)" class="btn">⬇️ 下载</button>
            </div>
          </div>
        </div>

        <div v-if="error" class="error-box">{{ error }}</div>
      </div>

      <!-- 使用量 -->
      <div class="card section">
        <h2 class="section-title">今日使用</h2>
        <div class="usage-info">
          <div class="usage-count">
            <span class="num">{{ auth.user?.daily_limit || 10 }}</span>
            <span class="label">每日限额</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 全屏图片 -->
    <div v-if="fullSizeImage" @click="fullSizeImage = null" class="fullscreen">
      <img :src="fullSizeImage" />
      <button class="fullscreen-close">✕</button>
    </div>
  </div>
</template>

<style scoped>
.workbench {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.section {
  padding: 20px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--t2);
  margin: 0 0 16px;
}

/* 模型选择 */
.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}

.model-card {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  text-align: left;
  cursor: pointer;
  transition: all var(--dur) var(--ease);
}

.model-card:hover {
  border-color: var(--accent);
  background: var(--surface-3);
}

.model-card.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 0 0 2px var(--accent-soft);
}

.model-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--t1);
  margin-bottom: 4px;
}

.model-desc {
  font-size: 11px;
  color: var(--t3);
}

/* 提示词 */
.prompt-area {
  margin-top: 20px;
}

.prompt-area label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--t2);
  margin-bottom: 8px;
}

.prompt-area textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--t1);
  font-size: 14px;
  resize: none;
  font-family: inherit;
}

.prompt-area textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.prompt-footer {
  text-align: right;
  font-size: 11px;
  color: var(--t3);
  margin-top: 4px;
}

/* 上传区域 */
.upload-area {
  margin-top: 16px;
}

.upload-area label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--t2);
  margin-bottom: 8px;
}

.upload-box {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all var(--dur) var(--ease);
}

.upload-box:hover {
  border-color: var(--accent);
}

.upload-placeholder {
  color: var(--t3);
}

.upload-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 11px;
  margin-top: 4px;
}

.upload-preview {
  position: relative;
  display: inline-block;
}

.upload-preview img {
  max-height: 120px;
  border-radius: var(--radius-sm);
}

.upload-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bad);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 12px;
}

.hidden {
  display: none;
}

/* 设置 */
.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
}

.form-group label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--t2);
  margin-bottom: 6px;
}

.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--t1);
  font-size: 13px;
}

/* 生成按钮 */
.full {
  width: 100%;
  justify-content: center;
  margin-top: 16px;
  padding: 12px;
}

/* 结果面板 */
.empty-state, .loading-state {
  text-align: center;
  padding: 48px 20px;
  color: var(--t3);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.loading-skeleton {
  width: 100%;
  height: 180px;
  background: var(--surface-2);
  border-radius: var(--radius);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  position: relative;
  border-radius: var(--radius);
  overflow: hidden;
}

.result-item img {
  width: 100%;
  display: block;
  cursor: pointer;
}

.result-actions {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px;
  background: linear-gradient(transparent, rgba(0,0,0,0.7));
  display: flex;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--dur) var(--ease);
}

.result-item:hover .result-actions {
  opacity: 1;
}

.error-box {
  padding: 12px;
  background: var(--bad-soft);
  color: var(--bad);
  border-radius: var(--radius-sm);
  font-size: 13px;
}

/* 使用量 */
.usage-info {
  text-align: center;
  padding: 16px;
}

.usage-count {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.usage-count .num {
  font-size: 32px;
  font-weight: 700;
  color: var(--accent);
}

.usage-count .label {
  font-size: 12px;
  color: var(--t3);
}

/* 全屏 */
.fullscreen {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.95);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.fullscreen img {
  max-width: 90%;
  max-height: 90%;
  border-radius: var(--radius);
}

.fullscreen-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 18px;
}

/* 响应式 */
@media (max-width: 900px) {
  .workbench {
    grid-template-columns: 1fr;
  }
  
  .workbench-side {
    order: -1;
  }
  
  .settings-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 500px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  
  .model-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
