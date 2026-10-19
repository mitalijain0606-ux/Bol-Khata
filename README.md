# Bol-Khata 🎤📕

**A voice-first AI credit manager for India's kirana stores — built on Gnani AI's Prisma, Timbre, and Evon.**

> Entry for the **Great Indian AI Internship Challenge** (Gnani AI) — theme: *Build Sovereign AI for India*.
> Trilingual (Hindi · Marathi · Tamil) · 100% synthetic data (DPDP-safe) · Solo build.

---

## The Problem

A typical kirana store has **₹40,000–50,000 stuck in informal credit (udhaar)** at any time. Three stacked problems:

1. **Bookkeeping friction** — the owner's hands are busy all day; typing entries into an app mid-sale never happens. Entries get missed, disputes follow.
2. **Money recovery** — chasing repayments is awkward and unstructured. Customers say *"kal pakka"* ("tomorrow, promise") and nobody tracks whether the promise was kept.
3. **Credit trust** — these customers have no credit history. Every *"should I lend ₹5,000 more?"* decision is memory and gut feeling.

Existing apps (Khatabook, OkCredit) digitized the notebook — **problem #1 only**. The money leaks in #2 and #3, and nobody solves those *by voice*.

## The Solution

**Bol-Khata is not an assistant — it's an employee.** It doesn't wait to be asked; it makes the calls, records the promises, and follows up.

| | Feature | What it does |
|---|---|---|
| 🎤 | **Voice ledger** | Speak in Hinglish: *"Sharma ji ko do hazaar paanch sau ka udhaar lagana"* → the entry writes itself (Hindi number words, honorific-aware name matching, ₹2,500). Queries too: *"kitna baki hai?"*, *"aaj ka hisaab"*. |
| 📞 | **Collections agent** | Proactively *calls* customers with overdue balances, listens to excuses, pushes back (harder if they broke a previous promise), and extracts a **promise-to-pay date** — tracked against actual payments. Three synthetic debtor personas make the demo repeatable. |
| 📊 | **Bharaut-Score** | Explainable per-customer trust score: broken promise −25 · late payment −10 · stale balance −5 · kept promise +5. Full breakdown in the UI — a shopkeeper only trusts a score he can audit. |
| 🌅 | **Morning briefing** | A spoken daily report: totals, nearest promise due, who broke a promise, how many calls to make today. |
| 🔒 | **Voice lock** | Owner enrolls ~5s of speech (ECAPA-TDNN embeddings, CPU). Destructive ledger actions require the owner's verified voice. |
| 🌍 | **Trilingual** | Hindi/Hinglish, Marathi, and Tamil — speech in, native-script replies out, in the same language. |
| 🔬 | **Noise harness** | Generates noisy test audio (0/5/10 dB SNR) and measures ASR word-error-rate — robustness as a chart, not a claim. |

## Where Gnani's models plug in

| Model | Role | Integration |
|---|---|---|
| **Prisma v2.5** (STT) | Hears the shopkeeper & call audio — code-mixed speech, telephony-grade | REST `POST /stt/v3` + streaming `wss://…/stt/v3/stream` (16-bit PCM), auto ITN numerals → *verified roundtrip with Timbre* |
| **Timbre v2.5** (TTS) | Speaks — agent uses **Poorvi (Hinglish voice)**; debtors use Deepak/Nalini/Kaveri; auto voice-pick for Marathi/Tamil | REST `POST /api/v1/tts/inference`, 16 kHz WAV |
| **Evon v3.3** (reasoning) | Thinks — tool-calling over the ledger (`add_entry`, `query_balance`, `log_promise`, `briefing`, `trust_score`) | OpenAI-compatible chat endpoint / HF open weights (Apache 2.0); deterministic Hinglish rule-engine fallback keeps the loop alive |

## Architecture

```
Phone / Laptop (React PWA)
        ⇅  WebSocket / REST
FastAPI backend
 ├── Speech layer ……… Gnani Prisma STT   (fallback: browser SpeechRecognition)
 ├── Brain ………………… Gnani Evon tools   (fallback: Hinglish rule engine + NLU)
 ├── Ledger tools ……… SQLite: entries, customers, promises, calls, scores
 ├── Call simulator …… 3 debtor personas, promise lifecycle, analytics
 └── Voice out ………… Gnani Timbre TTS   (fallback: browser speechSynthesis)
```

**Dual-mode by design:** every external capability has a free fallback, so the app runs at zero cost and never breaks on stage; setting `GNANI_API_KEY_ID` in `.env` switches the whole stack to Gnani with no code changes.

## Quick start

```bash
# Backend (Python 3.11+)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.seed_fake_data     # fake shop + 12 customers + history
.venv/bin/uvicorn app.main:app --port 8000

# Frontend (Node 18+)
cd ../frontend
npm install && npm run build                   # backend serves the built PWA

# Open http://localhost:8000 in Chrome (allow mic)
```

Runs immediately in **Mock Mode** (free, no keys). Optional voice lock: `pip install speechbrain torchaudio`.

### Switching to Gnani Mode

1. Copy `backend/.env.example` → `backend/.env`
2. Set `GNANI_API_KEY_ID=<your key from app.gnani.ai>`
3. Run `.venv/bin/python -m scripts.health_check` → all pings green
4. Restart — the header chip shows **Gnani Prisma·Timbre·Evon**

Evon activates when `EVON_API_URL` (OpenAI-compatible endpoint) or `EVON_HF_MODEL` (Hugging Face open weights) is set.

## How it works inside (highlights)

- **Hinglish NLU** — Hindi number-word composition (sau/hazaar/lakh), date parsing (*kal, parso, "15 tareekh", agle somvar* → ISO dates), honorific-stripping name matcher with vowel-fuzzy + consonant-skeleton matching so Devanagari/Tamil transcripts still resolve roman ledger names.
- **Promise lifecycle** — `PENDING → KEPT` (auto-settled when a payment arrives) `→ BROKEN` (due date passed) → feeds the trust score and the *tone* of the next collection call.
- **Call analytics** — every simulated call persists transcript, summary, sentiment, excuse type, outcome; a partial payment mid-call becomes a real ledger entry.
- **Every entry stores the raw spoken sentence** — an audit trail from any dashboard number back to the voice that created it.

## Privacy

Zero real personal data: fake names, fake phone numbers, synthesized voices, in-app simulated calls. Complies with the challenge's DPDP rule and makes demos infinitely repeatable.

## Repository map

```
backend/app/
  main.py            FastAPI routes + voice WebSocket
  agent/             NLU, brain (rules + Evon), collections call simulator
  gnani/             Prisma STT · Timbre TTS · Evon wrappers
  analytics/         Bharaut-Score, morning briefing
  voiceid/           speaker verification (ECAPA-TDNN)
backend/scripts/     seed_fake_data · health_check · make_noisy_testset
frontend/src/pages/  Khata (voice ledger) · CallScreen · Dashboard · Settings
docs/                plan, project explanation, video script, demo run-sheet
```

---

*Bol-Khata — give the khata a voice, the voice a memory, and the memory a credit score.*
