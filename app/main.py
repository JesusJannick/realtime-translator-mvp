from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Realtime Customer-Service Translator (MVP)")

# Static files (HTML)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Startseite = Chat-Website
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# WebSocket für Chat
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_json({"type": "system", "message": "WebSocket verbunden ✅"})
    try:
        while True:
            msg = await ws.receive_text()
            # Echo (später Übersetzung)
            await ws.send_json({
                "type": "message",
                "from": "server",
                "text": msg
            })
    except:
        await ws.close()