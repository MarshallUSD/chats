#!/bin/bash
# ──────────────────────────────────────────────
# 🚀 Скрипт деплоя ChatRoom на EC2 (Ubuntu)
#    Запустите на свежем EC2-инстансе:
#    bash deploy.sh
# ──────────────────────────────────────────────

set -e

echo "📦 Обновляем систему..."
sudo apt update && sudo apt upgrade -y

echo "🐍 Устанавливаем Python..."
sudo apt install -y python3 python3-pip python3-venv

echo "📂 Создаём виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

echo "📥 Устанавливаем зависимости..."
pip install -r requirements.txt

echo "🌐 Настраиваем Nginx..."
sudo apt install -y nginx

sudo tee /etc/nginx/sites-available/chatroom > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/chatroom /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo "⚙️  Создаём systemd-сервис..."
sudo tee /etc/systemd/system/chatroom.service > /dev/null <<SERVICE
[Unit]
Description=ChatRoom FastAPI App
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable chatroom
sudo systemctl start chatroom

echo ""
echo "✅ Готово! Чат запущен."
echo "🔗 Откройте в браузере: http://$(curl -s ifconfig.me)"
echo ""
echo "Полезные команды:"
echo "  sudo systemctl status chatroom   — статус"
echo "  sudo systemctl restart chatroom   — перезапуск"
echo "  sudo journalctl -u chatroom -f    — логи"
