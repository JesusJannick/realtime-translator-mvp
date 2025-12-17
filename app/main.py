from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Realtime Chat MVP")

# Static files (HTML)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_text("🟢 Verbindung hergestellt")

    while True:
        msg = await ws.receive_text()
        # ECHO (kommt später Übersetzung rein)
        await ws.send_text(f"Übersetzt: {msg}")