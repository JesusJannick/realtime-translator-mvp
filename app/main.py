from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI(title="Realtime Chat MVP")

HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Realtime Chat MVP</title>
<style>
body {
  background:#0f172a;
  color:white;
  font-family:system-ui;
  padding:20px
}
#chat {
  background:#020617;
  height:300px;
  overflow-y:auto;
  padding:10px;
  margin-top:10px;
  border-radius:8px
}
input,button {
  padding:10px;
  font-size:16px
}
.msg { margin-bottom:6px }
</style>
</head>
<body>

<h2>💬 Echtzeit-Chat (MVP)</h2>

<input id="text" placeholder="Nachricht eingeben…" />
<button onclick="send()">Senden</button>

<div id="chat"></div>

<script>
const chat = document.getElementById("chat");
const ws = new WebSocket(
  (location.protocol === "https:" ? "wss://" : "ws://") +
  location.host + "/ws"
);

ws.onmessage = e => {
  const d = document.createElement("div");
  d.className = "msg";
  d.innerText = e.data;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
};

function send() {
  const i = document.getElementById("text");
  ws.send(i.value);
  i.value = "";
}
</script>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    await ws.send_text("🟢 Verbindung hergestellt")

    while True:
        msg = await ws.receive_text()
        await ws.send_text(f"Echo: {msg}")