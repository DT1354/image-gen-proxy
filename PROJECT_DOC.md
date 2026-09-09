# ImageGen Proxy 项目完整文档

## 一、项目概述

### 目标
搭建一个图像生成代理服务，解决国内无法直接访问 apimart.ai API 的问题。

### 架构
```
国内用户 → Cloudflare (前端) → Azure 东京 VM (后端) → apimart.ai API
```

### 技术栈
- 前端：Vue 3 + Vite + Tailwind CSS
- 后端：FastAPI + Python
- 服务器：Azure VM (日本东京)
- 部署：systemd + Nginx + SSL
- 前端托管：Cloudflare Pages

### 服务器信息
- IP：20.243.178.68
- 系统：Ubuntu 24.04
- 规格：Standard D2s v3 (2 vCPU, 8 GiB)
- 位置：Japan East

---

## 二、项目结构

```
E:\image-gen-proxy\
├── backend/                    # 后端代码
│   ├── main.py                # FastAPI 主程序（API接口、图片生成逻辑）
│   ├── config.py              # 配置文件（读取 .env）
│   ├── requirements.txt       # Python 依赖
│   └── .env.example           # 环境变量示例
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── App.vue            # 主界面组件
│   │   ├── main.js            # Vue 入口文件
│   │   └── style.css          # 样式文件
│   ├── index.html             # HTML 入口
│   ├── package.json           # Node.js 依赖
│   ├── vite.config.js         # Vite 配置
│   ├── tailwind.config.js     # Tailwind 配置
│   └── postcss.config.js      # PostCSS 配置
├── scripts/                    # 部署脚本
│   ├── deploy-backend.sh      # 后端部署脚本
│   └── setup-nginx.sh         # Nginx + SSL 配置脚本
├── .gitignore                 # Git 忽略文件
└── README.md                  # 项目说明
```

---

## 三、后端部署（已完成）

### 服务器：Azure VM (20.243.178.68)

### 已完成的步骤：

#### 1. 上传文件到服务器
通过 FinalShell 上传到 `/tmp` 目录：
- main.py
- config.py
- requirements.txt
- .env.example
- deploy-backend.sh
- setup-nginx.sh

#### 2. 创建目录并移动文件
```bash
mkdir -p /tmp/backend
mv /tmp/main.py /tmp/config.py /tmp/requirements.txt /tmp/.env.example /tmp/backend/
```

#### 3. 执行部署脚本
```bash
chmod +x /tmp/deploy-backend.sh /tmp/setup-nginx.sh
sudo /tmp/deploy-backend.sh
```

脚本自动完成：
- 更新系统
- 安装 Python 3、pip、venv、nginx、certbot
- 创建 /var/www/image-gen-proxy 目录
- 创建 Python 虚拟环境并安装依赖
- 创建 systemd 服务 imagegen-proxy
- 启动服务

#### 4. 配置环境变量
```bash
cd /var/www/image-gen-proxy
sudo nano .env
```

内容：
```
APIMART_API_KEY=你的apimart密钥
ADMIN_KEY=你的管理密码
IMAGE_DIR=/var/www/image-gen-proxy/images
IMAGE_RETENTION_HOURS=24
DAILY_LIMIT=10
CORS_ORIGINS=http://localhost:5173
```

#### 5. 重启服务并测试
```bash
sudo systemctl restart imagegen-proxy
curl http://localhost:8000/health
curl http://20.243.178.68:8000/health
```

返回 `{"status":"ok"}` 表示成功。

#### 6. 配置 Nginx 和 SSL
```bash
sudo /tmp/setup-nginx.sh
```
输入域名（如 api.xxx.com）和邮箱，自动配置 SSL 证书。

---

## 四、Azure 端口开放

在 Azure 门户 → 虚拟机 → 网络 → 添加入站安全规则：

| 端口 | 协议 | 来源 | 说明 |
|------|------|------|------|
| 80 | TCP | Any (0.0.0.0/0) | HTTP |
| 443 | TCP | Any (0.0.0.0/0) | HTTPS |

8000 端口已经开放并测试通过。

---

## 五、域名配置（Cloudflare）

### DNS 记录配置

登录 Cloudflare → 选择域名 → DNS → 添加记录：

| 类型 | 名称 | 内容 | 代理状态 |
|------|------|------|----------|
| A | api | 20.243.178.68 | DNS only (灰色云朵) |

- 名称 `api` 表示二级域名 `api.你的域名.com`
- 代理状态必须选 **DNS only**，不能开代理

### 测试域名
```bash
ping api.你的域名.com
curl https://api.你的域名.com/health
```

---

## 六、前端部署（待完成）

### 方案 A：Cloudflare Pages 直接上传

1. 本地构建：
```bash
cd E:\image-gen-proxy\frontend
npm install
set VITE_API_BASE=https://api.你的域名.com
npm run build
```

2. Cloudflare → Workers & Pages → Create → Pages → Upload assets → 上传 dist 文件夹

### 方案 B：GitHub 自动部署（推荐）

1. 本地初始化 git 并推送：
```bash
cd E:\image-gen-proxy
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/你的用户名/image-gen-proxy.git
git push -u origin main
```

2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git → 选择仓库
   - Framework preset: Vue (Vite)
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Environment variables: `VITE_API_BASE` = `https://api.你的域名.com`

3. 部署后会得到一个域名：`image-gen.xxx.pages.dev`

---

## 七、后端 API 接口

### 基础信息
- Base URL: `https://api.你的域名.com`
- 服务地址: `http://localhost:8000`（服务器内部）

### 接口列表

#### 1. 健康检查
```
GET /health
返回: {"status": "ok"}
```

#### 2. 文生图
```
POST /api/generate/text
Content-Type: application/json

{
  "prompt": "提示词",
  "n": 1,
  "size": "4:3",
  "resolution": "4k",
  "reference_image": "base64或URL（可选）"
}

返回:
{
  "success": true,
  "images": ["/images/xxx.png"]
}
```

#### 3. 图生图
```
POST /api/generate/image
Content-Type: application/json

{
  "prompt": "提示词",
  "image": "base64编码的图片",
  "n": 1,
  "size": "4:3",
  "resolution": "4k"
}
```

#### 4. 获取支持的尺寸
```
GET /api/sizes

返回:
{
  "sizes": [
    {"value": "1:1", "label": "1:1 正方形"},
    {"value": "4:3", "label": "4:3 横版"},
    {"value": "3:4", "label": "3:4 竖版"},
    {"value": "16:9", "label": "16:9 宽屏"},
    {"value": "9:16", "label": "9:16 竖屏"}
  ],
  "resolutions": [
    {"value": "4k", "label": "4K 高清"},
    {"value": "2k", "label": "2K"},
    {"value": "1k", "label": "1K"}
  ]
}
```

#### 5. 查询任务状态
```
GET /api/task/{task_id}
```

---

## 八、环境变量说明

| 变量名 | 说明 | 当前值 |
|--------|------|--------|
| APIMART_API_KEY | apimart.ai API 密钥 | 已配置 |
| ADMIN_KEY | 管理员密钥 | 已配置 |
| IMAGE_DIR | 图片保存路径 | /var/www/image-gen-proxy/images |
| IMAGE_RETENTION_HOURS | 图片保留时间 | 24小时 |
| DAILY_LIMIT | 每日请求限额 | 10次 |
| CORS_ORIGINS | 允许的前端域名 | http://localhost:5173 |
| HOST | 服务监听地址 | 0.0.0.0 |
| PORT | 服务监听端口 | 8000 |

---

## 九、服务管理命令

```bash
# 查看服务状态
sudo systemctl status imagegen-proxy

# 重启服务
sudo systemctl restart imagegen-proxy

# 停止服务
sudo systemctl stop imagegen-proxy

# 查看日志
sudo journalctl -u imagegen-proxy -f

# 编辑配置
sudo nano /var/www/image-gen-proxy/.env
```

---

## 十、当前进度

| 步骤 | 状态 |
|------|------|
| 后端代码编写 | ✅ 完成 |
| 前端代码编写 | ✅ 完成 |
| 部署脚本编写 | ✅ 完成 |
| 后端部署到 Azure | ✅ 完成 |
| 环境变量配置 | ✅ 完成 |
| Nginx + SSL 配置 | ✅ 完成 |
| Azure 端口开放 | ✅ 完成 |
| 域名 DNS 配置 | ✅ 完成 |
| Git 初始化 | ⏳ 待执行 |
| 推送到 GitHub | ⏳ 待执行 |
| 前端部署到 Cloudflare | ⏳ 待执行 |

---

## 十一、待办事项

1. 初始化 git 仓库并推送到 GitHub
2. 在 Cloudflare Pages 连接 GitHub 仓库自动部署
3. 测试完整流程（前端 → 后端 → apimart.ai）

---

## 十二、常见问题

### Q: curl localhost 有响应，但外网访问不了？
A: 检查 Azure 端口是否开放（80、443）。

### Q: 保存 .env 文件提示 Permission denied？
A: 使用 sudo：`sudo nano /var/www/image-gen-proxy/.env`

### Q: npm install 报错？
A: 检查 Node.js 版本，建议 18+：`node -v`

### Q: Cloudflare Pages 部署后访问 404？
A: 检查构建输出目录是否为 `dist`，环境变量是否配置正确。

---

## 十三、费用说明

| 服务 | 费用 |
|------|------|
| Azure VM (D2s v3) | 约 $70/月（学生免费额度可能覆盖） |
| Cloudflare Pages | 免费 |
| 域名 | 约 $10/年 |
| apimart.ai API | 按调用量计费 |

---

文档完成时间：2026-09-02
