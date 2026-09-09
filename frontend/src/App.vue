<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
    <!-- Header -->
    <header class="border-b border-white/10 backdrop-blur-sm sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
            <span class="text-xl">🎨</span>
          </div>
          <div>
            <h1 class="text-xl font-bold">AI 图像工作台</h1>
            <p class="text-xs text-gray-400">GPT-Image-2 · 多模型支持</p>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <div class="text-sm text-gray-400">
            今日剩余: <span class="text-white font-medium">{{ usage.remaining }}</span> / {{ usage.limit }}
          </div>
          <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 py-6">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- Left Panel - Controls -->
        <div class="lg:col-span-2 space-y-6">
          
          <!-- Model Selection -->
          <div class="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
            <h2 class="text-sm font-medium text-gray-400 mb-4">选择模型</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <button
                v-for="model in models"
                :key="model.id"
                @click="selectedModel = model.id"
                :class="[
                  'p-4 rounded-xl text-left transition-all border',
                  selectedModel === model.id
                    ? 'bg-purple-500/20 border-purple-500 ring-2 ring-purple-500/50'
                    : 'bg-white/5 border-white/10 hover:bg-white/10'
                ]"
              >
                <div class="font-medium text-sm">{{ model.name }}</div>
                <div class="text-xs text-gray-400 mt-1">{{ model.description.split('，')[0] }}</div>
                <div class="flex flex-wrap gap-1 mt-2">
                  <span 
                    v-for="feat in model.features.slice(0, 2)" 
                    :key="feat"
                    class="text-xs px-2 py-0.5 bg-white/10 rounded"
                  >
                    {{ feat }}
                  </span>
                </div>
              </button>
            </div>
          </div>

          <!-- Mode Tabs -->
          <div class="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
            <div class="flex gap-2 mb-6">
              <button
                @click="mode = 'text2img'"
                :class="[
                  'flex-1 py-3 px-4 rounded-xl font-medium transition-all',
                  mode === 'text2img' 
                    ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg' 
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                ]"
              >
                <span class="mr-2">✏️</span> 文生图
              </button>
              <button
                @click="mode = 'img2img'"
                :class="[
                  'flex-1 py-3 px-4 rounded-xl font-medium transition-all',
                  mode === 'img2img' 
                    ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg' 
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                ]"
              >
                <span class="mr-2">🖼️</span> 图生图
              </button>
            </div>

            <!-- Prompt Input -->
            <div class="mb-6">
              <label class="block text-sm font-medium text-gray-300 mb-2">提示词</label>
              <textarea
                v-model="prompt"
                rows="4"
                class="w-full rounded-xl px-4 py-3 bg-white/5 border border-white/10 text-white placeholder-gray-500 resize-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/50 transition-all"
                placeholder="描述你想要生成的图像...&#10;&#10;例如：一只橘猫坐在窗台上看夕阳，水彩画风格"
              ></textarea>
              <div class="text-right text-xs text-gray-500 mt-1">{{ prompt.length }} / 4000</div>
            </div>

            <!-- Reference Image (img2img mode) -->
            <div v-if="mode === 'img2img'" class="mb-6">
              <label class="block text-sm font-medium text-gray-300 mb-2">参考图片</label>
              <div
                @click="triggerFileInput"
                @dragover.prevent
                @drop.prevent="handleDrop"
                class="border-2 border-dashed border-white/20 rounded-xl p-8 text-center cursor-pointer hover:border-purple-500 transition-colors"
              >
                <div v-if="!referenceImagePreview" class="text-gray-400">
                  <svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                  </svg>
                  <p class="font-medium">点击或拖拽上传图片</p>
                  <p class="text-sm mt-1">支持 JPG, PNG, WebP</p>
                </div>
                <div v-else class="relative inline-block">
                  <img :src="referenceImagePreview" class="max-h-48 rounded-lg shadow-lg" />
                  <button
                    @click.stop="clearReferenceImage"
                    class="absolute -top-2 -right-2 bg-red-500 rounded-full p-1.5 hover:bg-red-600 transition-colors shadow-lg"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                  </button>
                </div>
              </div>
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="handleFileSelect"
              />
            </div>

            <!-- Settings Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <!-- Size -->
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">尺寸</label>
                <select 
                  v-model="size" 
                  class="w-full rounded-xl px-4 py-3 bg-white/5 border border-white/10 text-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/50 transition-all"
                >
                  <option v-for="s in sizes" :key="s.value" :value="s.value" class="bg-slate-800">{{ s.label }}</option>
                </select>
              </div>

              <!-- Resolution -->
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">分辨率</label>
                <select 
                  v-model="resolution" 
                  class="w-full rounded-xl px-4 py-3 bg-white/5 border border-white/10 text-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/50 transition-all"
                >
                  <option v-for="r in resolutions" :key="r.value" :value="r.value" class="bg-slate-800">{{ r.label }}</option>
                </select>
              </div>

              <!-- Count -->
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">数量</label>
                <select 
                  v-model="count" 
                  class="w-full rounded-xl px-4 py-3 bg-white/5 border border-white/10 text-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/50 transition-all"
                >
                  <option v-for="n in 4" :key="n" :value="n" class="bg-slate-800">{{ n }} 张</option>
                </select>
              </div>

              <!-- Official Fallback -->
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">官方兜底</label>
                <button
                  @click="officialFallback = !officialFallback"
                  :class="[
                    'w-full rounded-xl px-4 py-3 transition-all border',
                    officialFallback
                      ? 'bg-green-500/20 border-green-500 text-green-400'
                      : 'bg-white/5 border-white/10 text-gray-400'
                  ]"
                >
                  {{ officialFallback ? '开启' : '关闭' }}
                </button>
              </div>
            </div>

            <!-- Generate Button -->
            <button
              @click="generate"
              :disabled="loading || !prompt.trim()"
              class="w-full py-4 rounded-xl font-medium bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-purple-500/25"
            >
              <span v-if="loading" class="flex items-center justify-center">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                生成中...
              </span>
              <span v-else>✨ 开始生成</span>
            </button>
          </div>
        </div>

        <!-- Right Panel - Results -->
        <div class="space-y-6">
          <!-- Results Panel -->
          <div class="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
            <h2 class="text-sm font-medium text-gray-400 mb-4">生成结果</h2>
            
            <!-- Empty State -->
            <div v-if="!images.length && !loading" class="h-96 flex items-center justify-center text-gray-500">
              <div class="text-center">
                <svg class="w-20 h-20 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
                <p class="font-medium">输入提示词开始创作</p>
                <p class="text-sm mt-1">支持文生图和图生图</p>
              </div>
            </div>

            <!-- Loading State -->
            <div v-if="loading" class="h-96 flex items-center justify-center">
              <div class="text-center">
                <div class="w-64 h-48 bg-white/5 rounded-xl mb-4 animate-pulse"></div>
                <p class="text-gray-400 animate-pulse">正在生成图像...</p>
              </div>
            </div>

            <!-- Results Grid -->
            <div v-if="images.length" class="space-y-4">
              <div
                v-for="(img, index) in images"
                :key="index"
                class="relative group rounded-xl overflow-hidden"
              >
                <img :src="img" class="w-full rounded-xl" />
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                  <div class="absolute bottom-4 left-4 right-4 flex gap-2">
                    <button
                      @click="downloadImage(img)"
                      class="flex-1 bg-white text-gray-900 py-2 px-4 rounded-lg font-medium text-center hover:bg-gray-100 transition-colors"
                    >
                      ⬇️ 下载
                    </button>
                    <button
                      @click="openFullSize(img)"
                      class="flex-1 bg-purple-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-purple-700 transition-colors"
                    >
                      🔍 查看大图
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Error State -->
            <div v-if="error" class="bg-red-500/20 border border-red-500/50 rounded-xl p-4 text-red-400">
              <div class="flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                {{ error }}
              </div>
            </div>
          </div>

          <!-- History Panel -->
          <div class="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
            <h2 class="text-sm font-medium text-gray-400 mb-4">最近生成</h2>
            <div v-if="history.length" class="space-y-2">
              <div
                v-for="(item, index) in history.slice(0, 5)"
                :key="index"
                class="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors"
                @click="loadHistory(item)"
              >
                <img :src="item.images[0]" class="w-12 h-12 rounded object-cover" />
                <div class="flex-1 min-w-0">
                  <div class="text-sm truncate">{{ item.prompt }}</div>
                  <div class="text-xs text-gray-500">{{ item.time }}</div>
                </div>
              </div>
            </div>
            <div v-else class="text-center text-gray-500 py-8">
              <p class="text-sm">暂无历史记录</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Full Size Image Modal -->
    <div
      v-if="fullSizeImage"
      @click="fullSizeImage = null"
      class="fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-4 cursor-pointer"
    >
      <img :src="fullSizeImage" class="max-w-full max-h-full object-contain rounded-xl" />
      <button
        @click="fullSizeImage = null"
        class="absolute top-4 right-4 bg-white/10 hover:bg-white/20 rounded-full p-3 transition-colors"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export default {
  name: 'App',
  data() {
    return {
      mode: 'text2img',
      selectedModel: 'gpt-image-2',
      prompt: '',
      referenceImage: null,
      referenceImagePreview: null,
      size: '1:1',
      resolution: '1k',
      count: 1,
      officialFallback: false,
      loading: false,
      images: [],
      error: null,
      fullSizeImage: null,
      usage: { used: 0, limit: 10, remaining: 10 },
      history: [],
      models: [],
      sizes: [
        { value: 'auto', label: '自动' },
        { value: '1:1', label: '1:1 正方形' },
        { value: '4:3', label: '4:3 横版' },
        { value: '3:4', label: '3:4 竖版' },
        { value: '16:9', label: '16:9 宽屏' },
        { value: '9:16', label: '9:16 竖屏' },
      ],
      resolutions: [
        { value: '1k', label: '1K 标准' },
        { value: '2k', label: '2K 高清' },
        { value: '4k', label: '4K 超高清' },
      ]
    }
  },
  async mounted() {
    await this.fetchModels()
    await this.fetchUsage()
    this.loadHistoryFromStorage()
  },
  methods: {
    async fetchModels() {
      try {
        const res = await axios.get(`${API_BASE}/api/models`)
        this.models = res.data.models
      } catch (e) {
        console.error('Failed to fetch models:', e)
      }
    },
    async fetchUsage() {
      try {
        const res = await axios.get(`${API_BASE}/api/usage`)
        this.usage = res.data
      } catch (e) {
        console.error('Failed to fetch usage:', e)
      }
    },
    triggerFileInput() {
      this.$refs.fileInput.click()
    },
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        this.processFile(file)
      }
    },
    handleDrop(event) {
      const file = event.dataTransfer.files[0]
      if (file && file.type.startsWith('image/')) {
        this.processFile(file)
      }
    },
    processFile(file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        this.referenceImage = e.target.result
        this.referenceImagePreview = e.target.result
      }
      reader.readAsDataURL(file)
    },
    clearReferenceImage() {
      this.referenceImage = null
      this.referenceImagePreview = null
      this.$refs.fileInput.value = ''
    },
    async generate() {
      if (!this.prompt.trim() || this.loading) return

      this.loading = true
      this.error = null
      this.images = []

      try {
        let response
        if (this.mode === 'text2img') {
          response = await axios.post(`${API_BASE}/api/generate/text`, {
            prompt: this.prompt,
            n: this.count,
            size: this.size,
            resolution: this.resolution,
            reference_images: this.referenceImage ? [this.referenceImage] : null,
            official_fallback: this.officialFallback
          })
        } else {
          response = await axios.post(`${API_BASE}/api/generate/image`, {
            prompt: this.prompt,
            image: this.referenceImage,
            n: this.count,
            size: this.size,
            resolution: this.resolution,
            official_fallback: this.officialFallback
          })
        }

        if (response.data.success) {
          this.images = response.data.images.map(img => `${API_BASE}${img}`)
          
          // Add to history
          this.history.unshift({
            prompt: this.prompt,
            images: this.images,
            time: new Date().toLocaleString(),
            model: this.selectedModel,
            size: this.size,
            resolution: this.resolution
          })
          this.saveHistoryToStorage()
          
          // Refresh usage
          await this.fetchUsage()
        } else {
          this.error = response.data.error || '生成失败，请重试'
        }
      } catch (err) {
        if (err.response?.status === 429) {
          this.error = '今日生成次数已用完，请明天再试'
        } else {
          this.error = err.response?.data?.detail || '生成失败，请重试'
        }
      } finally {
        this.loading = false
      }
    },
    openFullSize(url) {
      this.fullSizeImage = url
    },
    async downloadImage(url) {
      try {
        const localPath = url.replace(API_BASE, '')
        const response = await fetch(`${API_BASE}/api/download?url=${encodeURIComponent(localPath)}`)
        const blob = await response.blob()
        const downloadUrl = window.URL.createObjectURL(blob)
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
    },
    loadHistory(item) {
      this.prompt = item.prompt
      this.images = item.images
      this.size = item.size
      this.resolution = item.resolution
    },
    saveHistoryToStorage() {
      localStorage.setItem('imageGenHistory', JSON.stringify(this.history.slice(0, 20)))
    },
    loadHistoryFromStorage() {
      const saved = localStorage.getItem('imageGenHistory')
      if (saved) {
        this.history = JSON.parse(saved)
      }
    }
  }
}
</script>
