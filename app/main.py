import os
from typing import Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

APP_NAME = "Realtime Customer-Service Translator (MVP)"

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "").strip()
DEEPL_API_URL = os.getenv("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")

async def translate_text(text: str, target_lang: str, source_lang: Optional[str] = None) -> dict:
    text = (text or "").strip()
    if not text:
        return {"translated_text": "", "detected_source_lang": None, "provider": "none"}

    if DEEPL_API_KEY:
        payload = {"auth_key": DEEPL_API_KEY, "text": text, "target_lang": target_lang.upper()}
        if source_lang:
            payload["source_lang"] = source_lang.upper()

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(DEEPL_API_URL, data=payload)
            r.raise_for_status()
            data = r.json()
            t = data["translations"][0]
            return {
                "translated_text": t["text"],
                "detected_source_lang": t.get("detected_source_language"),
                "provider": "deepl",
            }

    return {"translated_text": f"[NO-API] {text}", "detected_source_lang": None, "provider": "fallback"}


app = FastAPI(title=APP_NAME)

# app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def index():
    return {
        "status": "ok",
        "message": "Realtime Translator API is running",
        "docs": "/docs",
        "websocket": "/ws"
    }

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    session = {"advisor_lang": "DE", "customer_lang": "EN"}
    try:
        await ws.send_json({"type": "hello", "session": session})
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "set_lang":
                if "advisor_lang" in msg:
                    session["advisor_lang"] = str(msg["advisor_lang"]).upper()
                if "customer_lang" in msg:
                    session["customer_lang"] = str(msg["customer_lang"]).upper()
                await ws.send_json({"type": "session", "session": session})
                continue

            if mtype == "chat":
                role = msg.get("role")
                text = msg.get("text", "")
                if role == "customer":
                    tr = await translate_text(text, session["advisor_lang"])
                    await ws.send_json({
                        "type": "chat_translated",
                        "from_role": "customer",
                        "to_role": "advisor",
                        "original": text,
                        "translated": tr["translated_text"],
                        "detected_source_lang": tr["detected_source_lang"],
                        "provider": tr["provider"],
                        "target_lang": session["advisor_lang"],
                    })
                elif role == "advisor":
                    tr = await translate_text(text, session["customer_lang"])
                    await ws.send_json({
                        "type": "chat_translated",
                        "from_role": "advisor",
                        "to_role": "customer",
                        "original": text,
                        "translated": tr["translated_text"],
                        "detected_source_lang": tr["detected_source_lang"],
                        "provider": tr["provider"],
                        "target_lang": session["customer_lang"],
                    })
                else:
                    await ws.send_json({"type": "error", "message": "Unknown role. Use 'customer' or 'advisor'."})
                continue

            await ws.send_json({"type": "error", "message": "Unknown message type."})

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        await ws.close()