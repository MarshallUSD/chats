# 💬 ChatRoom — Реалтайм чат на FastAPI

Простой чат с WebSocket для деплоя на AWS EC2.

## Что внутри

- **FastAPI** — бэкенд и WebSocket сервер
- **Встроенный фронтенд** — HTML/CSS/JS прямо в Python-файле
- **История сообщений** — последние 50 сообщений видны новым пользователям
- **Системные уведомления** — кто вошёл / вышел

## Локальный запуск

```bash
pip install -r requirements.txt
uvicorn app:app --reload
# Откройте http://localhost:8000
```

## Деплой на EC2 — пошагово

### 1. Создайте EC2-инстанс

- Зайдите в AWS Console → EC2 → **Launch Instance**
- **AMI:** Ubuntu Server 24.04 LTS
- **Тип:** t2.micro (Free Tier)
- **Key pair:** создайте новый или выберите существующий
- **Security Group:** откройте порты **22** (SSH) и **80** (HTTP)
- Нажмите **Launch Instance**

### 2. Подключитесь по SSH

```bash
chmod 400 your-key.pem
ssh -i "your-key.pem" ubuntu@<PUBLIC_IP>
```

### 3. Загрузите код на сервер

Вариант A — через Git:
```bash
git clone <ваш-репозиторий>
cd chatroom
```

Вариант B — через SCP (с вашего компьютера):
```bash
scp -i "your-key.pem" -r ./chatroom ubuntu@<PUBLIC_IP>:/home/ubuntu/
ssh -i "your-key.pem" ubuntu@<PUBLIC_IP>
cd chatroom
```

### 4. Запустите деплой

```bash
bash deploy.sh
```

Скрипт автоматически:
- Установит Python, pip, Nginx
- Создаст виртуальное окружение
- Настроит Nginx как реверс-прокси (с поддержкой WebSocket)
- Создаст systemd-сервис для автозапуска

### 5. Готово!

Откройте в браузере: `http://<PUBLIC_IP>`

## Полезные команды на сервере

```bash
sudo systemctl status chatroom      # статус приложения
sudo systemctl restart chatroom     # перезапуск
sudo journalctl -u chatroom -f      # логи в реальном времени
```

## Не забудьте!

После демонстрации **выключите (Terminate)** инстанс в AWS Console,
чтобы не тратить деньги.
