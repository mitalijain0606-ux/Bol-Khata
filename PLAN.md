# Bol-Khata — Project Plan
**"Khata ko awaaz do, awaaz ko yaaddasht, yaaddasht se ek credit manager."**
Solo build · Great Indian AI Internship Challenge · Deadline: **Nov 10, 2026, 11:59 PM IST**

---

## 1. Product (ek line me)

Dukaandaar ka AI manager — bolke khata likhta hai, bolke sawaal-sunta hai, due waale
customers ko khud call karke paise ka wada tulwaata hai, sirf malik ki awaaz se badalne
deta hai, aur har customer ka "bharaut-score" bana ke batata hai kise udhaar dena chahiye.

## 2. Free stack (total cost: ₹0)

| Kaam | Kya use hoga | Cost |
|---|---|---|
| Speech → Text (streaming, Hinglish) | Gnani Prisma v2.5 (program credits) | Free (5,000 credits registration ke saath) |
| Text → Speech (Hindi/Indic voices) | Gnani Timbre v2.5 (same credits) | Free (same credit pool) |
| Reasoning / agent brain | Gnani Evon v3.3 (open weights, Apache 2.0) | Free — HF pe request |
| Voice lock (sirf malik ki awaaz) | SpeechBrain ECAPA-TDNN (open source, CPU pe chalti hai) | Free |
| Backend | Python 3.11 + FastAPI (WebSocket + REST) | Free, open source |
| Database | SQLite (ek file, koi server nahi) | Free |
| Frontend | React + Vite + Tailwind, PWA ("Add to Home Screen") | Free |
| Phone demo connection | Cloudflare Tunnel (free) — laptop backend → phone | Free |
| Repo | GitHub (private bhi chalega) | Free |
| Video edit | CapCut (phone) | Free |

**Note:** Har registrant ko 5,000 program credits milte hain. Dashboard me credit usage
roz check karo; testing chhoti clips (5–10 sec) se karo, demo ke lamba portions
pre-record kar sakte ho taaki credits bach jaayein.

## 3. Architecture (kaise bahega)

```
Phone (PWA, mic)  ⇄  WebSocket  ⇄  FastAPI backend (laptop)
                                    ├─ Prisma STT  (audio → Hinglish text, streaming)
                                    ├─ Evon        (text → soch + TOOL CALL)
                                    ├─ TOOLS       (SQLite pe: add_entry, query_dues, …)
                                    ├─ Timbre TTS  (jawab → awaaz, streaming)
                                    ├─ SpeechBrain (voice lock: enroll + verify)
                                    └─ SQLite      (poora data)
```

Ek voice-entry ka flow: mic → Prisma → text → Evon (tool decide karta hai:
`add_entry`) → SQLite me entry → confirmation text → Timbre → awaaz phone pe.

## 4. Data design (SQLite tables)

- **shopkeeper** — id, name, language_pref, voice_profile (enrollment file path), created_at
- **customer** — id, shopkeeper_id, name, phone(FAKE), notes, created_at
- **entry** — id, shopkeeper_id, customer_id, type(`UDHAAR`/`PAYMENT`), amount,
  items_text, raw_transcript, status(`ACTIVE`/`SETTLED`), created_at
- **promise (wada)** — id, customer_id, amount, due_date, promised_on_call_id,
  status(`PENDING`/`KEPT`/`BROKEN`)
- **call** — id, customer_id, started_at, duration_sec, transcript(JSON), summary,
  sentiment, excuse_type, outcome(`PROMISE`/`REFUSED`/`NO_ANSWER`), promise_id
- **day_summary** — id, date, cash_in, udhaar_out, totals, mismatch_note, briefing_text
- **claim** (add-on) — customer self-claim: id, customer_id, amount, items_text,
  status(`PENDING`/`APPROVED`/`REJECTED`), created_at

**Trust Score (explainable formula, koi black box nahi):**
`score = 100 − 25×(tode hue wade) − 10×(der se payments) − 5×(bahut purane ACTIVE udhaar)`
Frontend me breakdown dikhana ("kyun 62 hai" — judges ko pasand aayega).

**Privacy rule (challenge ka hard rule):** sab data FAKE — seed_fake_data.py se
generated naam/number. Koi real recording, real number nahi.

## 5. Repo structure

```
bol-khata/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI: WS voice loop + REST (ledger, calls, dashboard)
│   │   ├── config.py          # .env loader (Gnani keys yahan)
│   │   ├── db.py  models.py   # SQLite + tables
│   │   ├── gnani/
│   │   │   ├── stt.py         # Prisma streaming WS wrapper
│   │   │   ├── tts.py         # Timbre SSE/WS wrapper
│   │   │   └── evon.py        # Evon chat + tool-calling wrapper
│   │   ├── agent/
│   │   │   ├── tools.py       # add_entry, query_dues, settle, log_promise, …
│   │   │   └── prompts.py     # system prompt (Hinglish persona, guardrails)
│   │   ├── voiceid/           # enroll.py, verify.py (SpeechBrain)
│   │   └── analytics/         # trust_score.py, call_summary.py, briefing.py
│   ├── scripts/
│   │   ├── health_check.py    # teeno Gnani API pe 1-1 test call → "all green"
│   │   ├── seed_fake_data.py  # fake shopkeeper + 12 customers + entries + wade
│   │   └── make_noisy_testset.py
│   └── requirements.txt
├── frontend/                  # Vite React PWA
│   └── src/pages: Khata · CallScreen · Dashboard · Onboarding(voice enroll)
├── demo/
│   ├── personas.json          # 3 debtor personalities (promiser/avoider/bargainer)
│   └── noise/                 # market noise clips (free sources)
├── docs/ (yeh file, video-script.md, demo-run-sheet.md)
└── README.md
```

## 6. Gnani API keys — setup flow (aaj hi karne wale steps)

1. **Register:** gnani.ai/great-indian-ai-internship-registration-form → 5,000 credits
   primary registrant ko milte hain.
2. **Login:** app.gnani.ai/voice → dashboard → **API key generate** (header:
   `X-API-Key-ID`). Key ko kisi ke saath share mat karo, screenshot me blur karo.
3. **Voice catalog browse:** 2–3 Hinglish/Hindi voices note karo (agent ke liye ek,
   fake customers ke liye 2 alag awaazein).
4. **Smoke test:** docs.gnani.ai quickstart se (a) 5-sec WAV pe STT REST call,
   (b) ek TTS REST call. Dono green = keys sahi. Credit usage check karo.
5. **Evon weights:** Hugging Face pe Evon v3.3 open-weights request **aaj hi bhejo** —
   approval me time lagta hai. Tab tak reasoning ka kaam platform API se chalao.
6. **Project me plug:** `.env` (gitignored) → `config.py` → `health_check.py` sab
   green confirm karega.
7. **Discord join** (challenge support channel).

## 7. 4-week milestones (solo, realistic)

| Hafta | Deliverable | "Done" matlab |
|---|---|---|
| 1 (13–19 Oct) | Voice khata core | Bolke entry + sawal-jawab (add/query/settle) chal raha hai; health_check green |
| 2 (20–26 Oct) | Collections agent | Call screen + fake customer se live baat + wada ledger me; **teaser post LinkedIn pe** |
| 3 (27–2 Nov) | Advanced layer | Voice lock + trust score + briefing + dashboard + 2nd language (Marathi ya Tamil) |
| 4 (3–9 Nov) | Polish + noise test + final 60s video | Nov 10 se pehle submit |

Kaatne ki priority agar time kam pade: dashboard/polish → noise test → 2nd language.
Core (voice khata + collections) kabhi nahi.

## 8. Demo plan (phone + laptop)

- Laptop pe backend; Cloudflare Tunnel se phone pe PWA khulega → "app" feel.
- Call screen me Timbre ki banavati awaazein = fake customers, live negotiation.
- 60s video arc: (1) dukaan me bolke entry (2) bolke sawal (3) agent ka live call +
  wada (4) trust score breakdown (5) closing number: "₹31,000 recovered of ₹47,000".
- Hashtags har post pe: #GreatIndianAIInternshipChallenge #GnaniAI

## 9. Aaj ki checklist (tumhare liye)

- [ ] Registration + credits activate
- [ ] API key generate
- [ ] Evon HF request bhejo (waiting time ka nuksaan na ho)
- [ ] Discord join
- [ ] GitHub repo `bol-khata` banao, yeh PLAN.md daal do
- [ ] Laptop me Python 3.11+ aur Node 18+ confirm karo
