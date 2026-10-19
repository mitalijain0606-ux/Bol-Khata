# Bol-Khata 🎤📕

**A voice-first credit manager for kirana stores — bolke khata, bolke vasooli.**

The shopkeeper just talks. The ledger writes itself, the app calls customers with
overdue balances, negotiates a repayment date, and scores how trustworthy each
customer is. No typing, no screens to hunt through — designed for people who are
busy, hands-full, and more comfortable speaking than tapping.

Trilingual: **Hinglish · मराठी · தமிழ்** — speak any of the three, get replies back
in the same language.

---

## Why

A typical kirana store has ₹40,000–50,000 stuck in informal credit (udhaar) at any
time, and the pain has three layers:

1. **Bookkeeping friction** — the owner's hands are busy all day; typing entries
   mid-sale never happens, so entries get missed.
2. **Money recovery** — chasing repayments is awkward and unstructured. Customers
   say *"kal pakka"* and nobody tracks whether the promise was kept.
3. **Credit trust** — these customers have no credit history, so every
   *"should I lend more?"* decision is gut feel.

Existing apps digitized the notebook — problem #1 only. Bol-Khata goes after all
three, by voice.

## Features

| | Feature | What it does |
|---|---|---|
| 🎤 | **Voice ledger** | *"Sharma ji ko do hazaar paanch sau ka udhaar lagana"* → the entry writes itself. Hindi number words, honorific-aware name matching, conversational queries (*"kitna baki hai?"*). |
| 📞 | **Collections agent** | Proactively calls customers with overdue balances, listens to excuses, pushes back (harder if they broke a previous promise), and extracts a **promise-to-pay date** — tracked against actual payments. |
| 📊 | **Bharaut-Score** | Explainable per-customer trust score: broken promise −25 · late payment −10 · stale balance −5 · kept promise +5. Full breakdown in the UI. |
| 🌅 | **Morning briefing** | A spoken daily report: totals, nearest promise due, who broke a promise, how many calls to make today. |
| 🔒 | **Voice lock** | Owner enrolls ~5s of speech (ECAPA-TDNN embeddings, CPU-friendly). Destructive ledger actions need the owner's verified voice. |
| 🌍 | **Trilingual** | Hinglish, Marathi, Tamil — speech in, native-script replies out. |
| 📱 | **Phone-first PWA** | Installs like an app, dark/light themes, phone-number + password login with per-account data isolation. |
| 🧪 | **Noise harness** | Generates noisy test audio (0/5/10 dB SNR) and measures ASR word-error-rate. |

And it's an **employee, not an assistant** — it doesn't wait to be asked. It makes
the calls, records the promises, follows up, and reports.

## Demo

> 📹 *(add a demo GIF or video here — the collections call is the money shot)*

Login with the seeded demo account and talk to it:

```
phone:    9876543210
password: demo1234
```

## Tech stack

- **Backend** — Python · FastAPI · WebSockets · SQLite
- **Frontend** — React · Vite · PWA (no app store needed)
- **Speech** — pluggable STT/TTS providers with a free browser-speech fallback
  (the app runs end-to-end at zero cost; drop API keys in `.env` to switch to
  cloud speech)
- **Brain** — tool-calling agent over the ledger (`add_entry`, `query_balance`,
  `log_promise`, `briefing`, `trust_score`) with a deterministic Hinglish NLU
  engine as the local fallback
- **Speaker verification** — SpeechBrain ECAPA-TDNN (optional install)

## Architecture

```
Phone / Laptop (React PWA)
        ⇅  REST / WebSocket
FastAPI backend
 ├── Speech layer …… cloud STT  (fallback: browser SpeechRecognition)
 ├── Brain ………………… tool-calling agent (fallback: Hinglish rule engine)
 ├── Ledger ……………… SQLite: entries, customers, promises, calls, scores
 ├── Call simulator …… debtor personas, promise lifecycle, analytics
 └── Voice out ………… cloud TTS  (fallback: browser speechSynthesis)
```

**Dual-mode by design:** every external capability has a free local fallback, so
the app never breaks on stage and costs nothing to run locally.

## Getting started

```bash
# Backend (Python 3.11+)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.seed_fake_data     # demo account + fake data
.venv/bin/uvicorn app.main:app --port 8000

# Frontend (Node 18+)
cd ../frontend
npm install && npm run build                   # backend serves the built PWA

# Open http://localhost:8000 → login (9876543210 / demo1234)
```

### Configuration

Copy `backend/.env.example` → `backend/.env` and add API keys for cloud speech
(STT/TTS) if you have them. Without keys the app runs in browser-speech mode.
Run `.venv/bin/python -m scripts.health_check` to verify provider connectivity.

## How it works inside (highlights)

- **Hinglish NLU** — Hindi number-word composition (sau/hazaar/lakh), date parsing
  (*kal, parso, "15 tareekh", agle somvar* → ISO dates), honorific-stripping name
  matcher with vowel-fuzzy + consonant-skeleton matching so Devanagari/Tamil
  transcripts still resolve roman ledger names.
- **Promise lifecycle** — `PENDING → KEPT` (auto-settled when a payment arrives)
  or `→ BROKEN` (due date passed) → feeds the trust score and the tone of the
  next collection call.
- **Call analytics** — every simulated call persists transcript, summary,
  sentiment, excuse type, outcome; a partial payment mid-call becomes a real
  ledger entry.
- **Audit trail** — every entry stores the raw spoken sentence it came from.

## Project structure

```
backend/app/
  main.py            FastAPI routes, auth, voice WebSocket
  agent/             NLU, brain (rules + tool-calling), collections simulator
  gnani/             STT / TTS / LLM provider wrappers
  analytics/         Bharaut-Score, morning briefing
  voiceid/           speaker verification
backend/scripts/     seed · health check · noise test set
frontend/src/pages/  Auth · Khata · CallScreen · Dashboard · Settings
docs/                plan, project explanation, demo run-sheet
```

## Notes & limitations

- All demo data is synthetic (fake names, fake numbers, synthesized voices) —
  the simulated calls run inside the app, no real telephony.
- Single-owner per deployment today; multi-tenant is straightforward schema work.
- Sentiment analysis is keyword-based; the voice lock's anti-spoofing is basic.

---

*Bol-Khata — give the khata a voice, the voice a memory, and the memory a credit score.*
