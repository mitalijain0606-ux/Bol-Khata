# Bol-Khata 🎤📕

**"Khata ko awaaz do, awaaz ko yaaddasht, aur yaaddasht se ek credit manager."**

Dukaandaar ka AI manager — **bolke khata** likhta hai, bolke sawaal-sunta hai, due waale
customers ko **khud call karke paise ka wada** tulwaata hai, ledger ko **malik ki awaaz se
lock** rakhta hai, aur har customer ka **Bharaut-Score** bana ke batata hai kise udhaar dena
chahiye.

> Great Indian AI Internship Challenge entry — built on Gnani AI (Prisma v2.5 · Timbre v2.5 ·
> Evon v3.3). Solo build. 100% synthetic data (DPDP-safe) — fake naam, fake numbers,
> banavati awaazein.

---

## Zero-cost dual mode (ya hi iska best feature hai)

| | Mock Mode (default) | Gnani Mode |
|---|---|---|
| STT | Browser SpeechRecognition (Chrome, free) | **Gnani Prisma v2.5** streaming WS |
| TTS | Browser speechSynthesis (free) | **Gnani Timbre v2.5** (Indic voices) |
| Brain | Hinglish rule engine (offline, deterministic) | **Gnani Evon v3.3** tool-calling |
| Cost | ₹0, aaj hi demo-ready | Free programme credits (5,000/registrant) |

`.env` me `GNANI_API_KEY_ID` bharo → restart → Settings page me sab **ACTIVE**.
Code same rehta hai — sirf providers switch hote hain.

## Features

1. **Bolke khata** — "Sharma ji ko do hazaar paanch sau ka udhaar" → entry (Hinglish number
   words parse hote hain), "kitna baki hai", "aaj ka hisaab" — sab voice.
2. **Vasooli call agent** — due waale customer pe tap karo; agent khud negotiate karta hai,
   excuse sunta hai, **wada ki date leta hai**, ledger me promise likhta hai.
   3 synthetic debtor personas: Pakka-wala 🙂, Talne-wala 😬, Bhav-taai-wala 🤝.
3. **Awaaz ka lock** — owner voice enroll (SpeechBrain ECAPA-TDNN, CPU pe free);
   delete/settle sirf owner ki awaaz pe (ARMour angle).
4. **Bharaut-Score** — explainable: wada toda −25, der se payment −10, purana baki −5,
   poora wada +5 (max +20). Breakdown UI me dikhta hai (ATLAS angle).
5. **Subah ki briefing** — AI manager ka morning report, bolke suna sakta hai.
6. **Noise test harness** — noisy-telephony test set generator + WER report
   (`python -m scripts.make_noisy_testset`) (Noise Canceller angle).

## Run (2 minute)

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.seed_fake_data        # fake dukaan + 12 customers
.venv/bin/uvicorn app.main:app --port 8000

# Frontend
cd ../frontend
npm install && npm run build                      # backend dist/ serve karta hai

# Browser (Chrome) -> http://localhost:8000
```

Optional voice lock: `pip install speechbrain torchaudio` (CPU chalega).

Phone pe demo: `cloudflared tunnel --url http://localhost:8000` → phone me kholo →
"Add to Home Screen" → PWA app ban jaata hai.

## Gnani Mode switch (jab keys milein)

1. `backend/.env` banao (`backend/.env.example` copy karo)
2. `GNANI_API_KEY_ID=` (app.gnani.ai dashboard se)
3. Quickstart (docs.gnani.ai) se exact endpoint paths confirm karke paths update karo
4. Evon: open-weights request approve hone par `EVON_HF_MODEL=` ya kisi compatible
   endpoint pe `EVON_API_URL=`
5. `.venv/bin/python -m scripts.health_check` → teeno pings green
6. Restart → Settings me sab ACTIVE

## Repo map

```
backend/app/       FastAPI: main.py (routes+WS), agent/ (brain+call sim),
                   gnani/ (Prisma/Timbre/Evon wrappers), analytics/, voiceid/
backend/scripts/   seed_fake_data · health_check · make_noisy_testset
frontend/src/      pages: Khata (voice ledger) · CallScreen · Dashboard · Settings
docs/              PLAN.md · demo-run-sheet.md · video-script.md
```

## Privacy

Poora data synthetic hai — DPDP Act ke hisaab se koi real phone number, Aadhaar, PAN,
ya recorded call use nahi hota. Debtor "calls" banavati awaaz ke saath app ke andar
simulate hote hain.
