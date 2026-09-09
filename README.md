# ImageGen Proxy

基于 apimart.ai API 的图像生成代理服务，解决国内访问问题。

## 架构

```
前端 (Vue) → 后端 (FastAPI) → apimart.ai API
   ↓              ↓
Cloudflare     Cloudflare 服务器
```

## 功能特性

- ✅ 文生图 (Text to Image)
- ✅ 图生图 (Image to Image)
- ✅ 多种尺寸和分辨率选择
- ✅ 多模型支持（GPT-Image-2、Imagen 4.0、Seedream、Flux 等）
- ✅ 每日请求限额
- ✅ 图片24小时自动清理

## 快速开始

### 1. 部署后端

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 APIMART_API_KEY

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. 部署前端

```bash
cd frontend

# 安装依赖
npm install

# 构建
VITE_API_BASE=https://api.your-domain.com npm run build

# 上传 dist 目录到 Cloudflare Pages
```

## API 接口

### 健康检查
```
GET /health
```

### 文生图
```
POST /api/generate/text
```

### 图生图
```
POST /api/generate/image
```

### 查询模型
```
GET /api/models
```

### 查询尺寸
```
GET /api/sizes
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| APIMART_API_KEY | apimart.ai API 密钥 | - |
| ADMIN_KEY | 管理员密钥 | - |
| DAILY_LIMIT | 每日请求限额 | 10 |

## License

MIT
