"""Bol-Khata API — REST + WebSocket voice loop.

  uvicorn app.main:app --reload --port 8000   (from backend/)
"""
import json
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import call_sim, tools as T
from app.agent.agent import handle_utterance, rule_reply
from app.analytics import trust_score
from app.analytics.briefing import build_briefing
from app.config import settings
from app.db import db, init_schema
from app.gnani import stt, tts
from app.gnani.stt import ProviderNotConfigured

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bolkhata")

app = FastAPI(title="Bol-Khata", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_schema()


# ---------------- health / mode ----------------

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "mode": settings.mode,
        "providers": {
            "stt_prisma": settings.stt_configured,
            "tts_timbre": settings.tts_configured,
            "evon": settings.evon_configured,
            "voice_lock": settings.voice_lock_enabled,
        },
    }


# ---------------- shopkeeper / voice enroll ----------------

@app.get("/api/shopkeeper")
def get_shopkeeper():
    with db() as conn:
        s = T.get_shopkeeper(conn)
        if not s:
            raise HTTPException(404, "Run seed first: python -m scripts.seed_fake_data")
        return dict(s)


@app.post("/api/shopkeeper/{sid}/enroll")
async def enroll_voice(sid: int, file: UploadFile = File(...)):
    from app.voiceid import voiceid
    wav = await file.read()
    res = voiceid.enroll(sid, wav)
    if not res.get("ok"):
        return JSONResponse(res, status_code=200)  # graceful: lock offline
    return res


@app.post("/api/shopkeeper/{sid}/verify-voice")
async def verify_voice(sid: int, file: UploadFile = File(...)):
    from app.voiceid import voiceid
    wav = await file.read()
    return voiceid.verify(sid, wav)


# ---------------- customers ----------------

class CustomerIn(BaseModel):
    name: str
    persona: str = ""
    phone: str = ""


@app.get("/api/customers")
def list_customers():
    with db() as conn:
        dues = {c["id"]: c for c in T.customers_with_dues(conn)}
        rows = conn.execute("SELECT * FROM customer ORDER BY name").fetchall()
        return [{**dict(r), "balance": dues.get(r["id"], {}).get("balance", 0.0)} for r in rows]


@app.post("/api/customers")
def add_customer(c: CustomerIn):
    with db() as conn:
        existing = T.find_customer(conn, c.name)
        if existing:
            raise HTTPException(409, f"{c.name} already in khata")
        row = T.create_customer(conn, c.name, persona=c.persona)
        return dict(row)


@app.get("/api/customers/{cid}/ledger")
def ledger(cid: int):
    with db() as conn:
        cust = conn.execute("SELECT * FROM customer WHERE id=?", (cid,)).fetchone()
        if not cust:
            raise HTTPException(404, "customer not found")
        entries = conn.execute(
            "SELECT * FROM entry WHERE customer_id=? ORDER BY id DESC LIMIT 50", (cid,)
        ).fetchall()
        promises = conn.execute(
            "SELECT * FROM promise WHERE customer_id=? ORDER BY id DESC", (cid,)
        ).fetchall()
        calls = conn.execute(
            "SELECT id, started_at, outcome, sentiment, summary FROM call_record WHERE customer_id=? ORDER BY id DESC LIMIT 10",
            (cid,),
        ).fetchall()
        return {"customer": dict(cust), "balance": T.customer_balance(conn, cid),
                "entries": [dict(e) for e in entries],
                "promises": [dict(p) for p in promises],
                "calls": [dict(c) for c in calls]}


# ---------------- entries / ledger ----------------

class EntryIn(BaseModel):
    customer_id: int
    type: str  # UDHAAR | PAYMENT
    amount: float
    items_text: str = ""
    raw_transcript: str = ""


@app.get("/api/entries")
def entries(limit: int = 30):
    with db() as conn:
        return [dict(e) for e in T.recent_entries(conn, limit)]


@app.post("/api/entries")
def add_entry(e: EntryIn):
    with db() as conn:
        cust = conn.execute("SELECT * FROM customer WHERE id=?", (e.customer_id,)).fetchone()
        if not cust:
            raise HTTPException(404, "customer not found")
        T.add_entry(conn, e.customer_id, e.type, e.amount, e.items_text, e.raw_transcript)
        if e.type == "PAYMENT":
            T.settle_due_promises(conn, e.customer_id, e.amount)
        return {"ok": True, "balance": T.customer_balance(conn, e.customer_id)}


@app.get("/api/totals")
def totals():
    with db() as conn:
        return T.totals(conn)


# ---------------- the brain ----------------

class UtterIn(BaseModel):
    text: str


@app.post("/api/voice/command")
async def voice_command(u: UtterIn):
    """Free-path brain (rule engine) — deterministic, used by Mock Mode too."""
    return rule_reply(u.text)


@app.post("/api/voice/agent")
async def voice_agent(u: UtterIn):
    """Full brain: Evon if configured, rules otherwise."""
    return await handle_utterance(u.text)


# ---------------- trust scores / briefing ----------------

@app.get("/api/trust-scores")
def trust_scores():
    with db() as conn:
        return trust_score.all_scores(conn)


@app.get("/api/briefing")
def briefing():
    with db() as conn:
        return build_briefing(conn)


# ---------------- TTS proxy (Gnani Mode) ----------------

@app.get("/api/tts")
async def tts_proxy(text: str, voice: str = "", lang: str = "hi-IN"):
    try:
        audio = await tts.synthesize(text, voice_id=voice, lang=lang)
        return Response(content=audio, media_type="audio/mpeg")
    except ProviderNotConfigured:
        return JSONResponse({"detail": "mock-mode: use browser speechSynthesis"}, status_code=204)
    except Exception as e:
        log.warning("TTS proxy failed: %s", e)
        return JSONResponse({"detail": str(e)}, status_code=502)


# ---------------- collections call simulator ----------------

@app.post("/api/call/start/{cid}")
def call_start(cid: int):
    res = call_sim.start_call(cid)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


@app.post("/api/call/{call_id}/step")
def call_step(call_id: int):
    res = call_sim.step_call(call_id)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


class SayIn(BaseModel):
    text: str


@app.post("/api/call/{call_id}/say")
def call_say(call_id: int, s: SayIn):
    res = call_sim.say_to_call(call_id, s.text)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


@app.post("/api/call/{call_id}/end")
def call_end(call_id: int):
    res = call_sim.end_call(call_id)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


# ---------------- realtime voice WS (Gnani streaming path) ----------------
# Mock Mode frontend sends {"type":"transcript","text":...} (browser STT).
# Gnani Mode sends binary PCM frames; backend streams to Prisma WS.

@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    await ws.accept()
    await ws.send_json({"type": "hello", "mode": settings.mode})
    prisma_ws = None
    try:
        while True:
            msg = await ws.receive()

            if msg.get("type") == "websocket.disconnect":
                break

            if (data := msg.get("bytes")) is not None and settings.stt_configured:
                if prisma_ws is None:
                    url = settings.gnani_base.replace("https", "wss").replace("http", "ws") + settings.stt_ws_path
                    import websockets
                    prisma_ws = await websockets.connect(url, extra_headers={"X-API-Key-ID": settings.gnani_api_key})
                await prisma_ws.send(data)
                try:
                    partial = await asyncio_wait_for(prisma_ws.recv(), timeout=0.5)
                    await ws.send_json({"type": "partial", "text": _partial_text(partial)})
                except TimeoutError:
                    pass
                continue

            if (raw := msg.get("text")) is not None:
                payload = json.loads(raw)
                if payload.get("type") == "transcript":
                    result = await handle_utterance(payload["text"])
                    await ws.send_json({"type": "result", **result})
                elif payload.get("type") == "flush" and prisma_ws is not None:
                    await prisma_ws.send(json.dumps({"type": "end"}))
                    final = await prisma_ws.recv()
                    await ws.send_json({"type": "transcript", "text": _partial_text(final)})
    except WebSocketDisconnect:
        pass
    finally:
        if prisma_ws:
            try:
                await prisma_ws.close()
            except Exception:
                pass


import asyncio  # noqa: E402  (used in ws loop)


def asyncio_wait_for(fut, timeout):
    return asyncio.wait_for(fut, timeout)


def _partial_text(raw) -> str:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "ignore")
    try:
        d = json.loads(raw)
        for key in ("transcript", "text", "display", "partial"):
            if d.get(key):
                return str(d[key])
    except Exception:
        pass
    return str(raw)[:200]


# ---------------- serve built frontend (single-server demo) ----------------

FRONTEND_DIST = __import__("pathlib").Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
