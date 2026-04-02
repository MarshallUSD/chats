"""
🗨️ Realtime Chat Room — FastAPI + WebSocket
Простой чат с реалтайм сообщениями.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from datetime import datetime
import json
import uuid

app = FastAPI(title="ChatRoom")


# ─── Менеджер подключений ───────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}
        self.usernames: dict[str, str] = {}
        self.history: list[dict] = []

    async def connect(self, websocket: WebSocket, client_id: str, username: str):
        await websocket.accept()
        self.active[client_id] = websocket
        self.usernames[client_id] = username

        # Отправляем историю новому пользователю
        for msg in self.history[-50:]:
            await websocket.send_text(json.dumps(msg))

        # Уведомляем всех
        await self.broadcast({
            "type": "system",
            "text": f"{username} присоединился к чату",
            "time": datetime.now().strftime("%H:%M"),
        })

    def disconnect(self, client_id: str):
        username = self.usernames.pop(client_id, "Аноним")
        self.active.pop(client_id, None)
        return username

    async def broadcast(self, message: dict):
        self.history.append(message)
        if len(self.history) > 200:
            self.history = self.history[-200:]
        data = json.dumps(message, ensure_ascii=False)
        for ws in list(self.active.values()):
            try:
                await ws.send_text(data)
            except:
                pass

    def online_count(self) -> int:
        return len(self.active)


manager = ConnectionManager()


# ─── WebSocket endpoint ─────────────────────────────────────────
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id, username)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({
                "type": "message",
                "user": username,
                "text": data,
                "time": datetime.now().strftime("%H:%M"),
            })
    except WebSocketDisconnect:
        left_user = manager.disconnect(client_id)
        await manager.broadcast({
            "type": "system",
            "text": f"{left_user} покинул чат",
            "time": datetime.now().strftime("%H:%M"),
        })


# ─── Главная страница ───────────────────────────────────────────
@app.get("/")
async def get():
    return HTMLResponse(HTML_PAGE)


# ─── Проверка здоровья ──────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "online": manager.online_count()}


# ─── HTML / CSS / JS ────────────────────────────────────────────
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>💬 ChatRoom</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;500;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface2: #1a1a26;
    --border: #2a2a3a;
    --text: #e8e8f0;
    --text-dim: #6e6e8a;
    --accent: #6c5ce7;
    --accent-glow: #6c5ce740;
    --green: #00cec9;
    --pink: #fd79a8;
    --orange: #e17055;
    --radius: 12px;
  }

  body {
    font-family: 'Outfit', sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100dvh;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  /* ── Фоновая сетка ── */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(108,92,231,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(108,92,231,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none;
  }

  /* ── Экран входа ── */
  #login-screen {
    text-align: center;
    animation: fadeUp 0.6s ease;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  #login-screen h1 {
    font-size: 2.4rem;
    font-weight: 700;
    margin-bottom: 8px;
    background: linear-gradient(135deg, var(--accent), var(--pink));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  #login-screen p {
    color: var(--text-dim);
    margin-bottom: 32px;
    font-size: 1rem;
    font-weight: 300;
  }

  .login-box {
    display: flex;
    gap: 10px;
  }

  .login-box input {
    font-family: 'Outfit', sans-serif;
    font-size: 1rem;
    padding: 14px 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    outline: none;
    width: 260px;
    transition: border-color 0.2s;
  }

  .login-box input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
  }

  .login-box button, #send-btn {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 14px 28px;
    border: none;
    border-radius: var(--radius);
    background: var(--accent);
    color: #fff;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
  }

  .login-box button:hover, #send-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 24px var(--accent-glow);
  }

  /* ── Чат ── */
  #chat-screen {
    display: none;
    width: 100%;
    max-width: 640px;
    height: 100dvh;
    flex-direction: column;
    animation: fadeUp 0.4s ease;
  }

  .chat-header {
    padding: 18px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    backdrop-filter: blur(12px);
    background: rgba(10,10,15,0.8);
  }

  .chat-header h2 {
    font-size: 1.15rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .online-dot {
    width: 8px; height: 8px;
    background: var(--green);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--green);
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .chat-header span {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
  }

  /* ── Сообщения ── */
  #messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }

  .msg {
    max-width: 85%;
    padding: 10px 16px;
    border-radius: 16px;
    font-size: 0.95rem;
    line-height: 1.45;
    word-break: break-word;
    animation: msgIn 0.25s ease;
  }

  @keyframes msgIn {
    from { opacity: 0; transform: translateY(8px) scale(0.97); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .msg.mine {
    align-self: flex-end;
    background: var(--accent);
    color: #fff;
    border-bottom-right-radius: 4px;
  }

  .msg.other {
    align-self: flex-start;
    background: var(--surface2);
    border-bottom-left-radius: 4px;
  }

  .msg .meta {
    font-size: 0.7rem;
    color: rgba(255,255,255,0.5);
    margin-bottom: 2px;
    font-family: 'JetBrains Mono', monospace;
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .msg.other .meta { color: var(--text-dim); }

  .msg .meta .author {
    font-weight: 600;
    color: var(--green);
  }

  .msg.mine .meta .author {
    color: rgba(255,255,255,0.8);
  }

  .msg.system {
    align-self: center;
    background: none;
    color: var(--text-dim);
    font-size: 0.8rem;
    font-style: italic;
    padding: 6px 0;
  }

  /* ── Ввод ── */
  .chat-input {
    padding: 16px 24px;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 10px;
    background: rgba(10,10,15,0.9);
    backdrop-filter: blur(12px);
  }

  .chat-input input {
    flex: 1;
    font-family: 'Outfit', sans-serif;
    font-size: 1rem;
    padding: 14px 18px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    outline: none;
    transition: border-color 0.2s;
  }

  .chat-input input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
  }

  @media (max-width: 660px) {
    #chat-screen { max-width: 100%; }
  }
</style>
</head>
<body>

<!-- Экран входа -->
<div id="login-screen">
  <h1>💬 ChatRoom</h1>
  <p>Реалтайм чат на FastAPI + WebSocket</p>
  <div class="login-box">
    <input type="text" id="username-input" placeholder="Ваше имя..." maxlength="20" autofocus>
    <button onclick="joinChat()">Войти →</button>
  </div>
</div>

<!-- Экран чата -->
<div id="chat-screen">
  <div class="chat-header">
    <h2><span class="online-dot"></span> ChatRoom</h2>
    <span id="user-label"></span>
  </div>
  <div id="messages"></div>
  <div class="chat-input">
    <input type="text" id="msg-input" placeholder="Написать сообщение..." autocomplete="off">
    <button id="send-btn" onclick="sendMessage()">↑</button>
  </div>
</div>

<script>
  let ws;
  let myName = '';

  const loginScreen = document.getElementById('login-screen');
  const chatScreen  = document.getElementById('chat-screen');
  const messagesDiv = document.getElementById('messages');
  const msgInput    = document.getElementById('msg-input');
  const nameInput   = document.getElementById('username-input');

  nameInput.addEventListener('keydown', e => { if (e.key === 'Enter') joinChat(); });
  msgInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

  function joinChat() {
    const name = nameInput.value.trim();
    if (!name) return;
    myName = name;

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws/${encodeURIComponent(name)}`);

    ws.onopen = () => {
      loginScreen.style.display = 'none';
      chatScreen.style.display = 'flex';
      document.getElementById('user-label').textContent = name;
      msgInput.focus();
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      appendMessage(msg);
    };

    ws.onclose = () => {
      appendMessage({ type: 'system', text: 'Соединение потеряно. Обновите страницу.' });
    };
  }

  function sendMessage() {
    const text = msgInput.value.trim();
    if (!text || !ws) return;
    ws.send(text);
    msgInput.value = '';
  }

  function appendMessage(msg) {
    const div = document.createElement('div');
    div.className = 'msg';

    if (msg.type === 'system') {
      div.classList.add('system');
      div.textContent = `— ${msg.text} —`;
    } else {
      const isMine = msg.user === myName;
      div.classList.add(isMine ? 'mine' : 'other');
      div.innerHTML = `
        <div class="meta">
          <span class="author">${esc(msg.user)}</span>
          <span>${msg.time}</span>
        </div>
        ${esc(msg.text)}
      `;
    }

    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }
</script>
</body>
</html>
"""
