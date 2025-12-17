import os
from typing import Optional

import httpx
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

APP_NAME = "Realtime Customer-Service Translator (MVP)"

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
DEEPL_API_URL = os.getenv("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")

app = FastAPI(title=APP_NAME)


# ---------------------------
# Translation Helper
# ---------------------------
async def translate_text(
    text: str,
    target_lang: str,
    source_lang: Optional[str] = None
):
    text = (text or "").strip()
    if not text:
        return {"translated_text": "", "provider": "none"}

    if DEEPL_API_KEY:
        payload = {
            "auth_key": DEEPL_API_KEY,
            "text": text,
            "target_lang": target_lang
        }
        if source_lang:
            payload["source_lang"] = source_lang

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(DEEPL_API_URL, data=payload)
            r.raise_for_status()
            data = r.json()
            t = data["translations"][0]
            return {
                "translated_text": t["text"],
                "detected_source_lang": t.get("detected_source_language"),
                "provider": "deepl"
            }

    # Fallback ohne API
    return {
        "translated_text": f"[NO-API] {text}",
        "provider": "mock"
    }


# ---------------------------
# HTTP Root
# ---------------------------
@app.get("/")
async def index():
    return {
        "status": "ok",
        "message": "Realtime Translator API is running",
        "docs": "/docs",
        "websocket": "/ws"
    }


# ---------------------------
# WebSocket
# ---------------------------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()

    session = {
        "advisor_lang": "DE",
        "customer_lang": "EN"
    }

    await ws.send_json({
        "type": "hello",
        "session": session
    })

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "set_lang":
                if "advisor_lang" in msg:
                    session["advisor_lang"] = msg["advisor_lang"]
                if "customer_lang" in msg:
                    session["customer_lang"] = msg["customer_lang"]

                await ws.send_json({
                    "type": "lang_updated",
                    "session": session
                })

            elif mtype == "translate":
                text = msg.get("text", "")
                direction = msg.get("direction", "customer_to_advisor")

                if direction == "customer_to_advisor":
                    source = session["customer_lang"]
                    target = session["advisor_lang"]
                else:
                    source = session["advisor_lang"]
                    target = session["customer_lang"]

                result = await translate_text(
                    text=text,
                    source_lang=source,
                    target_lang=target
                )

                await ws.send_json({
                    "type": "translation",
                    "direction": direction,
                    "original_text": text,
                    "translated_text": result["translated_text"],
                    "provider": result["provider"]
                })

    except Exception:
        await ws.close()
                    