from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Realtime Chat MVP")

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# HTML Chat
@app.get("/", response_class=HTMLResponse)
async def chat():
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# API Status (verschoben!)
@app.get("/api")
async def api_status():
    return JSONResponse({
        "status": "ok",
        "message": "Realtime Chat API is running",
        "websocket": "/ws"
    })

# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_text("🟢 Verbindung hergestellt")

    while True:
        msg = await ws.receive_text()
        await ws.send_text(f"Echo: {msg}")