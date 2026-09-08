#!/bin/bash
# Nginx 配置和 SSL 证书申请脚本
# 在 Azure Ubuntu VM 上执行

set -e

echo "=========================================="
echo "  Nginx 和 SSL 配置脚本"
echo "=========================================="

# 读取域名
read -p "请输入你的域名 (例如: api.example.com): " DOMAIN
read -p "请输入你的邮箱 (用于SSL证书): " EMAIL

# 1. 创建 Nginx 配置
echo "[1/3] 配置 Nginx..."
sudo tee /etc/nginx/sites-available/imagegen-proxy > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # SSL配置（申请证书后启用）
    # listen 443 ssl;
    # ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    location /images/ {
        alias /var/www/image-gen-proxy/images/;
        expires 24h;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 2. 启用站点
sudo ln -sf /etc/nginx/sites-available/imagegen-proxy /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# 3. 申请 SSL 证书
echo "[2/3] 申请 SSL 证书..."
sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

# 4. 设置自动续期
echo "[3/3] 设置证书自动续期..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

echo "=========================================="
echo "  Nginx 和 SSL 配置完成！"
echo "  访问地址: https://$DOMAIN"
echo "=========================================="
