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
@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return HTMLResponse("""
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Echtzeit-Übersetzer Chat (MVP)</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;margin:16px}
    .row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
    select,input,button{font-size:16px;padding:10px}
    input{flex:1;min-width:220px}
    .box{border:1px solid #ddd;border-radius:10px;padding:12px;margin-top:12px}
    .muted{opacity:.7;font-size:14px}
    pre{white-space:pre-wrap;word-wrap:break-word}
  </style>
</head>
<body>
  <h2>🗣️ Echtzeit-Kundendienstübersetzer (Chat MVP)</h2>
  <div class="muted">Verbinde zu: <span id="wsUrl"></span></div>

  <div class="row">
    <label>Kunde:
      <select id="customerLang">
        <option value="EN">EN</option>
        <option value="FR">FR</option>
        <option value="TR">TR</option>
        <option value="AR">AR</option>
        <option value="ES">ES</option>
        <option value="IT">IT</option>
      </select>
    </label>

    <label>Berater:
      <select id="advisorLang">
        <option value="DE" selected>DE</option>
        <option value="EN">EN</option>
        <option value="FR">FR</option>
        <option value="TR">TR</option>
        <option value="AR">AR</option>
        <option value="ES">ES</option>
      </select>
    </label>

    <label>Richtung:
      <select id="direction">
        <option value="customer_to_advisor" selected>Kunde → Berater</option>
        <option value="advisor_to_customer">Berater → Kunde</option>
      </select>
    </label>

    <button id="connectBtn">Verbinden</button>
  </div>

  <div class="row">
    <input id="text" placeholder="Text eingeben…" />
    <button id="sendBtn" disabled>Übersetzen</button>
  </div>

  <div class="box">
    <div><b>Antwort</b> <span class="muted" id="status"></span></div>
    <pre id="out">Noch nichts…</pre>
  </div>

<script>
let ws;

function makeWsUrl(){
  const proto = (location.protocol === "https:") ? "wss" : "ws";
  return proto + "://" + location.host + "/ws";
}

const wsUrlEl = document.getElementById("wsUrl");
wsUrlEl.textContent = makeWsUrl();

const statusEl = document.getElementById("status");
const outEl = document.getElementById("out");
const sendBtn = document.getElementById("sendBtn");

function log(obj){
  outEl.textContent = JSON.stringify(obj, null, 2);
}

document.getElementById("connectBtn").onclick = () => {
  const url = makeWsUrl();
  statusEl.textContent = " (verbinde…)";
  ws = new WebSocket(url);

  ws.onopen = () => {
    statusEl.textContent = " ✅ verbunden";
    sendBtn.disabled = false;

    // Sprache setzen
    ws.send(JSON.stringify({
      type: "set_lang",
      customer_lang: document.getElementById("customerLang").value,
      advisor_lang: document.getElementById("advisorLang").value
    }));
  };

  ws.onmessage = (ev) => {
    try { log(JSON.parse(ev.data)); }
    catch { outEl.textContent = ev.data; }
  };

  ws.onclose = () => {
    statusEl.textContent = " ❌ getrennt";
    sendBtn.disabled = true;
  };

  ws.onerror = () => {
    statusEl.textContent = " ❌ Fehler";
  };
};

document.getElementById("sendBtn").onclick = () => {
  if(!ws || ws.readyState !== 1){
    alert("Nicht verbunden. Erst auf 'Verbinden' drücken.");
    return;
  }
  const text = document.getElementById("text").value;
  const direction = document.getElementById("direction").value;

  ws.send(JSON.stringify({
    type: "translate",
    direction,
    text
  }));
};
</script>
</body>
</html>
    """)