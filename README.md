# ImageGen Proxy

基于 apimart.ai API 的图像生成代理服务，解决国内访问问题。

## 架构

```
前端 (Vue) → 后端 (FastAPI) → apimart.ai API
   ↓              ↓
Cloudflare     Azure 东京 VM
```

## 项目结构

```
image-gen-proxy/
├── backend/               # 后端代码
│   ├── main.py           # FastAPI 主程序
│   ├── config.py         # 配置文件
│   ├── requirements.txt  # Python 依赖
│   └── .env.example      # 环境变量示例
├── frontend/             # 前端代码
│   ├── src/
│   │   ├── App.vue       # 主组件
│   │   ├── main.js       # 入口文件
│   │   └── style.css     # 样式文件
│   ├── package.json
│   └── vite.config.js
├── scripts/              # 部署脚本
│   ├── deploy-backend.sh
│   └── setup-nginx.sh
└── README.md
```

## 功能特性

- ✅ 文生图 (Text to Image)
- ✅ 图生图 (Image to Image)
- ✅ 多种尺寸和分辨率选择
- ✅ 每日请求限额
- ✅ 图片24小时自动清理
- ✅ SSL HTTPS 支持
- ✅ 管理员认证

## 快速开始

### 1. 部署后端 (Azure VM)

```bash
# 上传文件到 Azure VM
scp -r backend/* scripts/* user@20.243.178.68:/tmp/

# SSH 登录 Azure VM
ssh user@20.243.178.68

# 执行部署脚本
chmod +x /tmp/scripts/*.sh
/tmp/scripts/deploy-backend.sh

# 配置环境变量
cd /var/www/image-gen-proxy
cp .env.example .env
nano .env  # 填入你的 APIMART_API_KEY 和 ADMIN_KEY

# 配置 Nginx 和 SSL
/tmp/scripts/setup-nginx.sh
```

### 2. 部署前端 (Cloudflare Pages)

```bash
cd frontend

# 安装依赖
npm install

# 构建
VITE_API_BASE=https://api.your-domain.com npm run build

# 上传 dist 目录到 Cloudflare Pages
```

### 3. 配置域名

在你的域名服务商添加 DNS 记录：

```
类型: A
名称: api
值: 20.243.178.68
```

## API 接口

### 文生图

```
POST /api/generate/text
Content-Type: application/json

{
  "prompt": "一只橘猫坐在窗台上",
  "n": 1,
  "size": "4:3",
  "resolution": "4k",
  "reference_image": "base64或URL（可选）"
}
```

### 图生图

```
POST /api/generate/image
Content-Type: application/json

{
  "prompt": "变成水彩画风格",
  "image": "base64编码的图片",
  "n": 1,
  "size": "4:3",
  "resolution": "4k"
}
```

### 获取支持的尺寸

```
GET /api/sizes
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| APIMART_API_KEY | apimart.ai API 密钥 | - |
| ADMIN_KEY | 管理员密钥 | - |
| IMAGE_DIR | 图片保存路径 | /var/www/image-gen-proxy/images |
| IMAGE_RETENTION_HOURS | 图片保留时间（小时） | 24 |
| DAILY_LIMIT | 每日请求限额 | 10 |
| CORS_ORIGINS | 允许的前端域名 | http://localhost:5173 |

## 管理员功能

- 查看系统状态
- 管理用户限额
- 手动清理图片

## License

MIT
