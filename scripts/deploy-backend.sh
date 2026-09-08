#!/bin/bash
# ImageGen Proxy 后端部署脚本
# 在 Azure Ubuntu VM 上执行

set -e

echo "=========================================="
echo "  ImageGen Proxy 后端部署脚本"
echo "=========================================="

# 配置
APP_DIR="/var/www/image-gen-proxy"
IMAGE_DIR="/var/www/image-gen-proxy/images"
SERVICE_NAME="imagegen-proxy"

# 1. 更新系统
echo "[1/7] 更新系统..."
sudo apt update && sudo apt upgrade -y

# 2. 安装依赖
echo "[2/7] 安装 Python 和依赖..."
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# 3. 创建目录
echo "[3/7] 创建应用目录..."
sudo mkdir -p $APP_DIR
sudo mkdir -p $IMAGE_DIR

# 4. 复制文件（假设已上传到 /tmp）
echo "[4/7] 复制应用文件..."
sudo cp /tmp/backend/* $APP_DIR/
sudo chown -R $USER:$USER $APP_DIR

# 5. 创建虚拟环境
echo "[5/7] 创建 Python 虚拟环境..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. 创建 systemd 服务
echo "[6/7] 创建系统服务..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=ImageGen Proxy API
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "=========================================="
echo "  后端部署完成！"
echo "  服务状态: sudo systemctl status $SERVICE_NAME"
echo "  查看日志: sudo journalctl -u $SERVICE_NAME -f"
echo "=========================================="
