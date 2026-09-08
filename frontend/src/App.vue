<template>
  <div class="min-h-screen text-white p-4 md:p-8">
    <!-- Header -->
    <header class="text-center mb-8">
      <h1 class="text-4xl md:text-5xl font-bold gradient-text mb-2">AI 图像生成</h1>
      <p class="text-gray-400">基于 GPT-Image-2 的智能图像创作平台</p>
    </header>

    <!-- Main Container -->
    <div class="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Left Panel - Controls -->
      <div class="glass-card rounded-2xl p-6">
        <!-- Mode Tabs -->
        <div class="flex gap-2 mb-6">
          <button
            @click="mode = 'text2img'"
            :class="[
              'flex-1 py-3 px-4 rounded-xl font-medium transition-all',
              mode === 'text2img' 
                ? 'bg-indigo-600 text-white' 
                : 'bg-slate-700/50 text-gray-400 hover:bg-slate-700'
            ]"
          >
            <span class="mr-2">✏️</span> 文生图
          </button>
          <button
            @click="mode = 'img2img'"
            :class="[
              'flex-1 py-3 px-4 rounded-xl font-medium transition-all',
              mode === 'img2img' 
                ? 'bg-indigo-600 text-white' 
                : 'bg-slate-700/50 text-gray-400 hover:bg-slate-700'
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
            class="w-full rounded-xl px-4 py-3 text-white placeholder-gray-500 resize-none"
            placeholder="描述你想要生成的图像..."
          ></textarea>
        </div>

        <!-- Reference Image (img2img mode) -->
        <div v-if="mode === 'img2img'" class="mb-6">
          <label class="block text-sm font-medium text-gray-300 mb-2">参考图片</label>
          <div
            @click="triggerFileInput"
            @dragover.prevent
            @drop.prevent="handleDrop"
            class="border-2 border-dashed border-slate-600 rounded-xl p-6 text-center cursor-pointer hover:border-indigo-500 transition-colors"
          >
            <div v-if="!referenceImagePreview" class="text-gray-400">
              <svg class="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
              </svg>
              <p>点击或拖拽上传图片</p>
            </div>
            <div v-else class="relative">
              <img :src="referenceImagePreview" class="max-h-40 mx-auto rounded-lg" />
              <button
                @click.stop="clearReferenceImage"
                class="absolute top-2 right-2 bg-red-500 rounded-full p-1 hover:bg-red-600"
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
        <div class="grid grid-cols-2 gap-4 mb-6">
          <!-- Size -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">尺寸</label>
            <select v-model="size" class="w-full rounded-xl px-4 py-3">
              <option v-for="s in sizes" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>

          <!-- Resolution -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">分辨率</label>
            <select v-model="resolution" class="w-full rounded-xl px-4 py-3">
              <option v-for="r in resolutions" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <!-- Count -->
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-300 mb-2">生成数量: {{ count }}</label>
            <input
              v-model="count"
              type="range"
              min="1"
              max="4"
              class="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>
        </div>

        <!-- Generate Button -->
        <button
          @click="generate"
          :disabled="loading || !prompt.trim()"
          class="w-full btn-primary text-white font-medium py-4 rounded-xl"
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

        <!-- Usage Info -->
        <div class="mt-4 text-center text-sm text-gray-400">
          每日免费额度: {{ dailyLimit }} 次
        </div>
      </div>

      <!-- Right Panel - Results -->
      <div class="glass-card rounded-2xl p-6">
        <h2 class="text-lg font-medium text-gray-300 mb-4">生成结果</h2>
        
        <!-- Empty State -->
        <div v-if="!images.length && !loading" class="h-96 flex items-center justify-center text-gray-500">
          <div class="text-center">
            <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
            </svg>
            <p>输入提示词开始创作</p>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="h-96 flex items-center justify-center">
          <div class="text-center">
            <div class="skeleton w-64 h-48 rounded-xl mb-4"></div>
            <p class="text-gray-400 animate-pulse">正在生成图像...</p>
          </div>
        </div>

        <!-- Results Grid -->
        <div v-if="images.length" class="grid grid-cols-1 gap-4">
          <div
            v-for="(img, index) in images"
            :key="index"
            class="relative group image-preview rounded-xl overflow-hidden"
          >
            <img :src="img" class="w-full rounded-xl" />
            <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
              <a
                :href="img"
                download
                class="bg-white text-gray-900 px-4 py-2 rounded-lg font-medium hover:bg-gray-100 transition-colors"
              >
                <span class="mr-2">⬇️</span> 下载
              </a>
              <button
                @click="openFullSize(img)"
                class="bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors"
              >
                <span class="mr-2">🔍</span> 查看大图
              </button>
            </div>
          </div>
        </div>

        <!-- Error State -->
        <div v-if="error" class="bg-red-500/20 border border-red-500 rounded-xl p-4 text-red-400">
          {{ error }}
        </div>
      </div>
    </div>

    <!-- Full Size Image Modal -->
    <div
      v-if="fullSizeImage"
      @click="fullSizeImage = null"
      class="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4 cursor-pointer"
    >
      <img :src="fullSizeImage" class="max-w-full max-h-full object-contain rounded-xl" />
      <button
        @click="fullSizeImage = null"
        class="absolute top-4 right-4 bg-white/10 hover:bg-white/20 rounded-full p-2"
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
      prompt: '',
      referenceImage: null,
      referenceImagePreview: null,
      size: '4:3',
      resolution: '4k',
      count: 1,
      loading: false,
      images: [],
      error: null,
      fullSizeImage: null,
      dailyLimit: 10,
      sizes: [
        { value: '1:1', label: '1:1 正方形' },
        { value: '4:3', label: '4:3 横版' },
        { value: '3:4', label: '3:4 竖版' },
        { value: '16:9', label: '16:9 宽屏' },
        { value: '9:16', label: '9:16 竖屏' },
      ],
      resolutions: [
        { value: '4k', label: '4K 高清' },
        { value: '2k', label: '2K' },
        { value: '1k', label: '1K' },
      ]
    }
  },
  methods: {
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
            reference_image: this.referenceImage
          })
        } else {
          response = await axios.post(`${API_BASE}/api/generate/image`, {
            prompt: this.prompt,
            image: this.referenceImage,
            n: this.count,
            size: this.size,
            resolution: this.resolution
          })
        }

        if (response.data.success) {
          this.images = response.data.images.map(img => `${API_BASE}${img}`)
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
    }
  }
}
</script>
