"""Bol-Khata API — REST + WebSocket voice loop + phone/password auth.

  uvicorn app.main:app --reload --port 8000   (from backend/)
"""
import asyncio
import json
import logging
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import auth
from app.agent import call_sim, tools as T
from app.agent.agent import handle_utterance, rule_reply, run_tool
from app.analytics import trust_score
from app.analytics.briefing import build_briefing
from app.config import settings
from app.db import db, init_schema
from app.speech import stt, tts
from app.speech.stt import ProviderNotConfigured

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bolkhata")

app = FastAPI(title="Bol-Khata", version="1.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_schema()


def _sid(request: Request) -> int:
    """Shopkeeper id from the Bearer token (falls back to the seeded account)."""
    return auth.sid_from_token(request.headers.get("authorization")) or 1


# ---------------- auth ----------------

class RegisterIn(BaseModel):
    name: str
    shop_name: str = ""
    phone: str
    password: str


class LoginIn(BaseModel):
    phone: str
    password: str


def _clean_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p or "")
    return digits[-10:] if len(digits) >= 10 else ""


@app.post("/api/auth/register")
def register(r: RegisterIn):
    phone = _clean_phone(r.phone)
    if not phone:
        raise HTTPException(400, "Sahi 10-digit phone number daaliye")
    if len(r.password or "") < 4:
        raise HTTPException(400, "Password kam se kam 4 character ka rakhiye")
    with db() as conn:
        existing = conn.execute("SELECT id FROM shopkeeper WHERE phone = ?", (phone,)).fetchone()
        if existing:
            raise HTTPException(409, "Ye number pehle se registered hai — login kijiye")
        cur = conn.execute(
            "INSERT INTO shopkeeper (name, shop_name, phone, password_hash) VALUES (?, ?, ?, ?)",
            (r.name.strip() or "Dukaandaar", r.shop_name.strip(), phone, auth.hash_password(r.password)),
        )
        sid = cur.lastrowid
    return {"token": auth.make_token(sid),
            "shopkeeper": {"id": sid, "name": r.name, "shop_name": r.shop_name, "phone": phone}}


@app.post("/api/auth/login")
def login(r: LoginIn):
    phone = _clean_phone(r.phone)
    with db() as conn:
        row = conn.execute("SELECT * FROM shopkeeper WHERE phone = ?", (phone,)).fetchone()
    if not row or not row["password_hash"] or not auth.verify_password(r.password, row["password_hash"]):
        raise HTTPException(401, "Phone ya password galat hai")
    return {"token": auth.make_token(row["id"]),
            "shopkeeper": {"id": row["id"], "name": row["name"], "shop_name": row["shop_name"], "phone": phone}}


@app.get("/api/auth/me")
def me(request: Request):
    sid = auth.sid_from_token(request.headers.get("authorization"))
    if not sid:
        raise HTTPException(401, "not logged in")
    with db() as conn:
        row = T.get_shopkeeper(conn, sid)
    if not row:
        raise HTTPException(401, "account not found")
    return {"id": row["id"], "name": row["name"], "shop_name": row["shop_name"],
            "phone": row["phone"], "voice_enrolled": bool(row["voice_profile_path"])}


# ---------------- health ----------------

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "mode": ("cloud" if settings.mode == "gnani" else "mock"),
        "providers": {
            "stt": settings.stt_configured,
            "tts": settings.tts_configured,
            "brain": settings.evon_configured,
            "voice_lock": settings.voice_lock_enabled,
        },
    }


# ---------------- shopkeeper / voice enroll ----------------

@app.get("/api/shopkeeper")
def get_shopkeeper(request: Request):
    with db() as conn:
        s = T.get_shopkeeper(conn, _sid(request))
        if not s:
            raise HTTPException(404, "Account not found — register first")
        return dict(s)


@app.post("/api/shopkeeper/{sid}/enroll")
async def enroll_voice(sid: int, file: UploadFile = File(...)):
    from app.voiceid import voiceid
    wav = await file.read()
    res = voiceid.enroll(sid, wav)
    return JSONResponse(res, status_code=200)


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
def list_customers(request: Request):
    sid = _sid(request)
    with db() as conn:
        dues = {c["id"]: c for c in T.customers_with_dues(conn, sid)}
        rows = conn.execute(
            "SELECT * FROM customer WHERE shopkeeper_id = ? ORDER BY name", (sid,)
        ).fetchall()
        return [{**dict(r), "balance": dues.get(r["id"], {}).get("balance", 0.0)} for r in rows]


@app.post("/api/customers")
def add_customer(c: CustomerIn, request: Request):
    sid = _sid(request)
    with db() as conn:
        existing = T.find_customer(conn, c.name, sid)
        if existing:
            raise HTTPException(409, f"{c.name} already in khata")
        row = T.create_customer(conn, c.name, shopkeeper_id=sid, persona=c.persona)
        return dict(row)


@app.get("/api/customers/{cid}/ledger")
def ledger(cid: int, request: Request):
    sid = _sid(request)
    with db() as conn:
        cust = conn.execute(
            "SELECT * FROM customer WHERE id = ? AND shopkeeper_id = ?", (cid, sid)
        ).fetchone()
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
def entries(limit: int = 30, request: Request = None):
    with db() as conn:
        return [dict(e) for e in T.recent_entries(conn, limit, _sid(request))]


@app.post("/api/entries")
def add_entry(e: EntryIn, request: Request):
    sid = _sid(request)
    with db() as conn:
        cust = conn.execute(
            "SELECT * FROM customer WHERE id=? AND shopkeeper_id=?", (e.customer_id, sid)
        ).fetchone()
        if not cust:
            raise HTTPException(404, "customer not found")
        T.add_entry(conn, e.customer_id, e.type, e.amount, e.items_text, e.raw_transcript, shopkeeper_id=sid)
        if e.type == "PAYMENT":
            T.settle_due_promises(conn, e.customer_id, e.amount)
        return {"ok": True, "balance": T.customer_balance(conn, e.customer_id)}


@app.get("/api/totals")
def totals(request: Request):
    with db() as conn:
        return T.totals(conn, _sid(request))


# ---------------- the brain ----------------

class UtterIn(BaseModel):
    text: str
    lang: str = "hi-IN"


@app.post("/api/stt")
async def stt_proxy(file: UploadFile = File(...), lang: str = ""):
    """Mic audio (wav, recorded+encoded in browser) -> cloud STT -> transcript."""
    try:
        audio = await file.read()
        text = await stt.transcribe_clip(audio, lang=lang)
        return {"transcript": text, "provider": "prisma"}
    except ProviderNotConfigured:
        return {"transcript": "", "provider": "mock"}
    except Exception as e:
        log.warning("STT proxy failed: %s", e)
        raise HTTPException(502, str(e))


@app.post("/api/voice/command")
async def voice_command(u: UtterIn, request: Request):
    """Free-path brain (rule engine) — deterministic."""
    return rule_reply(u.text, u.lang, _sid(request))


@app.post("/api/voice/agent")
async def voice_agent(u: UtterIn, request: Request):
    """Full brain: cloud reasoning if configured, rules otherwise."""
    return await handle_utterance(u.text, u.lang, _sid(request))


# ---------------- trust scores / briefing ----------------

@app.get("/api/trust-scores")
def trust_scores(request: Request):
    with db() as conn:
        return trust_score.all_scores(conn, _sid(request))


@app.get("/api/briefing")
def briefing(request: Request):
    with db() as conn:
        return build_briefing(conn, _sid(request))


# ---------------- TTS proxy ----------------

@app.get("/api/tts")
async def tts_proxy(text: str, voice: str = "", lang: str = "hi-IN"):
    try:
        audio = await tts.synthesize(text, voice=voice, lang=lang)
        return Response(content=audio, media_type="audio/wav")
    except ProviderNotConfigured:
        return JSONResponse({"detail": "mock-mode: use browser speechSynthesis"}, status_code=204)
    except Exception as e:
        log.warning("TTS proxy failed: %s", e)
        return JSONResponse({"detail": str(e)}, status_code=502)


# ---------------- collections call simulator ----------------

@app.post("/api/call/start/{cid}")
def call_start(cid: int, request: Request):
    sid = _sid(request)
    with db() as conn:
        own = conn.execute(
            "SELECT 1 FROM customer WHERE id=? AND shopkeeper_id=?", (cid, sid)
        ).fetchone()
        if not own:
            raise HTTPException(404, "customer not found")
    res = call_sim.start_call(cid, sid)
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


# ---------------- realtime voice WS ----------------

@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    await ws.accept()
    await ws.send_json({"type": "hello", "mode": ("cloud" if settings.mode == "gnani" else "mock")})
    prisma_ws = None
    try:
        while True:
            msg = await ws.receive()

            if msg.get("type") == "websocket.disconnect":
                break

            if (data := msg.get("bytes")) is not None and settings.stt_configured:
                if prisma_ws is None:
                    from app.speech.stt import open_stream
                    prisma_ws = await open_stream()
                await prisma_ws.send(data)
                try:
                    partial = await asyncio.wait_for(prisma_ws.recv(), timeout=0.5)
                    await ws.send_json({"type": "partial", "text": _partial_text(partial)})
                except TimeoutError:
                    pass
                continue

            if (raw := msg.get("text")) is not None:
                payload = json.loads(raw)
                if payload.get("type") == "transcript":
                    result = await handle_utterance(payload["text"], payload.get("lang", "hi-IN"))
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

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
