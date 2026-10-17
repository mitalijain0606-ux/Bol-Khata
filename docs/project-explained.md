# Bol-Khata — The Complete Project Explanation (Study Guide)

> Padho, samjho, apne shabdon me bolo. Interview me har component tumse
> individually poocha ja sakta hai — ye doc har "kyun" ka jawab rakhta hai.

---

## 1. WHAT THE PROJECT IS

**Bol-Khata is an AI credit manager for kirana stores, built by voice.** The
shopkeeper talks to it in Hinglish; it writes the ledger, answers questions,
calls customers who owe money, negotiates repayment dates, records promises,
and scores how trustworthy each customer is.

Two facts define it:
1. It is **not an assistant** (answers when asked) — it is an **employee**
   (does work nobody asked for: outbound collection calls, follow-ups, reports).
2. Its outcome is **money recovered**, not clever replies. That's the line that
   separates it from every "voice chatbot" entry.

Built for: Gnani AI's Great Indian AI Internship Challenge (deadline Nov 10,
2026; up to 100 paid 6-month internships, stipend up to ₹1L/month).
Rule: must use Gnani's models — Prisma (STT), Timbre (TTS), Evon (reasoning).
Theme: "Build Sovereign AI for India". Hard rule: 100% synthetic data (DPDP Act).

## 2. THE PROBLEM (three layers deep)

A typical kirana store has **₹40–50k stuck in udhaar** at any time.

- **Layer 1 — Writing:** owner's hands are busy 14 hours a day; typing entries
  into an app mid-sale never happens. Missed entries → disputes → lost money.
- **Layer 2 — Recovery:** reminding customers is socially awkward and
  unstructured. "Kal pakka" is never tracked. Nobody knows who promised what.
- **Layer 3 — Trust:** udhaar customers have no CIBIL. Every "should I give
  ₹5,000 more?" decision is memory + gut.

Khatabook/OkCredit solved Layer 1 only (digital notebook). Bol-Khata attacks
**all three** — and layers 2+3 are where the money actually is.

Why VOICE is the right interface: hands/eyes busy → speech is the only free
channel; shopkeepers already speak transactions aloud; works across literacy
levels; India speaks code-mixed Hinglish, not app-English.

## 3. THE JOURNEY OF ONE VOICE COMMAND (how it actually works)

Say the user speaks: *"Sharma ji ko do hazaar paanch sau ka udhaar lagana"*

1. **Mic capture** (browser) — audio goes to the speech layer.
2. **STT** — Gnani Mode: streamed to **Prisma** (`POST /stt/v3` REST or the
   `/stt/v3/stream` WebSocket with 16-bit PCM frames; auth header
   `X-API-Key-ID`). Mock Mode: browser SpeechRecognition. Output: transcript text.
3. **Brain** — the agent layer decides intent and action.
   - **Gnani Mode:** transcript → **Evon 3.3** with a tool schema
     (`add_entry`, `query_balance`, `totals_today`, `list_dues`, `briefing`,
     `trust_score`). Evon returns a tool call → backend executes it.
   - **Mock Mode:** a deterministic Hinglish rule engine (no API cost).
4. **Action** — backend writes to SQLite (the ledger), e.g. entry:
   customer=Rajesh Sharma, type=UDHAAR, amount=2500.
5. **Reply** — confirmation text goes to **Timbre** (`POST /api/v1/tts/inference`,
   model `timbre-v2.5`, voice `Poorvi` — a Hinglish voice) → audio bytes.
   Mock Mode: browser speechSynthesis.
6. **UI** — the ledger screen refreshes; the reply bubble + spoken audio play.

Total design rule: the brain has two interchangeable engines, every effect goes
through the same tool functions, so switching brains never changes behavior.

## 4. ARCHITECTURE (components + why)

```
Phone/Laptop (React PWA)  ⇄  WebSocket/REST  ⇄  FastAPI backend
   - mic, TTS playback                          ├─ speech layer (Prisma / browser)
   - 4 screens                                  ├─ brain (Evon / rule engine)
                                                ├─ tools (ledger operations)
                                                ├─ call simulator (personas)
                                                ├─ analytics (trust, briefing)
                                                └─ SQLite (single file, zero cost)
```

Key decisions and WHY:
- **SQLite, not Postgres:** solo hackathon build → zero infra, zero cost,
  trivially resettable (reseed fake data in one command). Honest trade-off to
  say in interview: "production would use Postgres; nothing in the schema is
  SQLite-specific."
- **FastAPI:** WebSockets + async (needed for streaming voice) with plain REST
  for everything else.
- **React PWA, no app store:** phone is the shopkeeper's device; PWA gives an
  app-like "Add to Home Screen" experience without store review delays. Demo
  runs on a laptop backend + phone client via a tunnel.
- **Dual-mode providers:** every external capability has a free fallback
  (browser STT/TTS, rule brain). This meant: unlimited free testing, the demo
  never breaks on stage, and the Gnani switch is one `.env` line — no code
  change. (Endpoints are wired to Gnani's exact documented APIs.)

## 5. FEATURES — HOW EACH ONE WORKS INSIDE

### A. Voice ledger + Hinglish NLU
- **Number parser:** a dictionary of Hindi number words 1–99 plus multipliers
  (sau ×100, hazaar ×1,000, lakh ×100,000) with composition rules — so
  "do hazaar paanch sau" → 2,500. Handles digits too ("2500"), and strips
  date fragments first so "19 October" never becomes ₹19 (real bug I caught
  and fixed).
- **Name matching:** people say "Sharma ji" but the ledger stores "Rajesh
  Sharma". Matching removes honorifics (ji/bhai/seth) and matches on any
  significant token — longest token first. If no match: creates the customer.
- **Intent classification:** pattern rules for PAYMENT ("diya/diye/jama"),
  ADD_UDHAAR ("udhaar/likh do"), QUERY_BALANCE ("kitna baki"), SETTLE,
  BRIEFING, TOTALS, LIST_DUES, SCORE — ordered so overlapping phrasing still
  resolves correctly (payment checked before udhaar).
- **Audit trail:** every entry stores the raw spoken sentence it came from.

### B. Collections call agent + debtor simulator (the differentiator)
- The shopkeeper taps a customer with dues → a call screen opens.
- A **server-side state machine** drives the negotiation:
  `OPEN → EXCUSED → NEGOTIATE → SETTLED_PROMISE / PARTIAL / REFUSED`
  with a turn cap. The agent's lines adapt to context: a customer with a broken
  promise gets a sterner opening; excuses get acknowledged then redirected to
  "give me one firm date".
- **Three synthetic debtor personas** (Pakka-wala agrees fast, Talne-wala
  deflects, Bhav-taai-wala offers partial payment) so the demo is repeatable,
  watchable, and needs zero real phone numbers.
- **Promise extraction:** the debtor's line is parsed for a date (kal, parso,
  "15 tareekh", "agle somvar" — all mapped to ISO dates) and optionally a
  partial amount (only accepted if it's ≥10% of the balance — the guard that
  stopped "19 October" being read as ₹19).
- **On call end:** the call record is persisted with full transcript, a summary,
  sentiment (keyword-based), excuse type, outcome (PROMISE / PARTIAL / REFUSED);
  the promise row is created; a partial payment (if any) becomes a PAYMENT entry.
- **Shopkeeper barge-in:** the owner can speak mid-call; the debtor reacts.
  (This is the seed of real barge-in handling.)

### C. Bharaut-Score (trust score)
- Formula: `100 − 25×broken_promises − 10×late_payments − 5×stale_balance
  + 5×kept_promises (max +20)`, clamped 0–100.
- Bands: ≥80 Pakka · ≥55 Theek-thaak · ≥35 Sambhal ke · <35 Risky.
- **Explainable by design** — the UI shows the exact breakdown ("why 75?").
  A shopkeeper will only act on a score he can audit; and explainability is
  what makes it a *credit signal* rather than a black box.
- Inputs: promise outcomes (kept/broken/overdue), payment lateness vs. first
  udhaar date, and balance staleness (30+ days).

### D. Morning briefing
Generated from live data: totals, today's cash, nearest promise due (with
name+amount), a warning naming whoever last broke a promise, the largest
outstanding balance, count of calls to make, and a risky-customer flag. Spoken
aloud on tap. This is the feature that makes it feel like an employee: it
tells you what to do before you ask.

### E. Voice lock (security)
- Owner enrolls ~5s of speech → **ECAPA-TDNN speaker embedding** (SpeechBrain,
  open source, CPU) stored on disk.
- Destructive actions (delete/settle/waive) require cosine-similarity ≥ 0.55
  against the enrolled embedding. Counter chatter can't touch the ledger.
- This mirrors Gnani's **ARMour** voice-biometrics product line — said
  explicitly in interviews. Honest limitation: current anti-spoofing is basic;
  a replay/clone detector is roadmap work.

### F. Noise robustness harness
Script generates synthetic test sentences, mixes market/traffic noise at
0/5/10 dB SNR (pure-Python mixing, no dependencies), and with keys configured
runs batch STT to produce a WER-vs-SNR report (JSON + printable). Turns
"it works in noise" from a claim into a chart (the challenge's "Noise
Canceller" award angle).

## 6. DATA MODEL (7 tables, and how they connect)

- `shopkeeper` — the owner + enrolled voice profile
- `customer` — belongs to a shopkeeper; carries a persona (for simulation)
- `entry` — UDHAAR or PAYMENT; amount, items, raw transcript, status
- `promise` — customer, amount, due_date, status PENDING→KEPT/BROKEN; linked
  to the call that produced it
- `call_record` — transcript JSON, summary, sentiment, excuse type, outcome,
  duration; linked to the promise it created
- `day_summary` — daily totals + briefing text
- `claim` — (add-on) customer self-claims pending owner approval

Relationships that matter: entry→customer, promise→customer + call, so the
trust score can be computed by pure SQL over history, and every number on the
dashboard traces back to a spoken sentence.

## 7. WHERE EACH GNANI MODEL PLUGS IN (exact)

- **Prisma v2.5 (STT):** REST `POST {base}/stt/v3` — multipart `audio_file` +
  `language_code` (hi-IN etc.) → `{transcript}`. Realtime:
  `wss://{base}/stt/v3/stream` — headers `x-api-key-id` + `lang_code`, 16-bit
  mono PCM frames. Used for: shopkeeper commands, call-side speech.
- **Timbre v2.5 (TTS):** `POST {base}/api/v1/tts/inference` — JSON with `text`,
  `model: timbre-v2.5`, `voice` (catalog name — agent uses **Poorvi**, a
  Hinglish voice; customers use Deepak/Nalini/Kaveri), `language`, and
  `audio_config` (16 kHz wav) → raw audio bytes. Correct lakh/crore numerals
  matter because amounts are the product.
- **Evon 3.3 (reasoning):** open weights (Apache 2.0, 30B/128K context/11
  Indic languages) accessed via an OpenAI-compatible chat endpoint with the
  tool schema; a second Evon pass phrases the tool result into natural
  Hinglish. Falls back to the rule engine if Evon is unavailable — never
  crashes the voice loop.

## 8. THE DUAL-MODE DESIGN (why it's the smartest part of the build)

Mock Mode (browser STT/TTS + rule engine) and Gnani Mode (Prisma/Timbre/Evon)
are interchangeable because all effects flow through the same tool layer.
Benefits: unlimited free iteration (credits are finite: 5,000), a demo that
cannot fail on stage due to network/quota, and a clean production path — the
final video is shot in Gnani Mode per the challenge's "must use Gnani models"
rule. In interviews this reads as: environment abstraction, graceful
degradation, cost awareness.

## 9. WHAT WAS TESTED & REAL BUGS FIXED (engineering story — tell this)

- Seeded 12 fake customers, 30 days of entries, promises in all states →
  dashboard and scores exercised with realistic data.
- Browser-tested every flow end-to-end: voice entry, balance query, full call
  negotiation to a recorded promise, score breakdowns, briefing playback.
- **Bug 1:** "19 October" parsed as ₹19 partial payment → fixed with date-
  fragment stripping + a "partial must be ≥10% of balance" rule.
- **Bug 2:** call auto-negotiation stalled — a React closure held a stale null
  call id → fixed with a ref; call-end now always completes.
- **Bug 3:** my synthetic health-check WAV was malformed → replaced with a
  valid 16 kHz silent WAV so the STT ping is real.
- Trust-score variety: seed data spans 100 (Pakka) to 0 (Risky) so every band
  is demonstrable.

## 10. PRIVACY & ETHICS (say this before being asked)

Zero real personal data: fake names/numbers, synthesized debtor voices, in-app
simulated calls (no telephony). Complies with the challenge's DPDP rule and
makes demos repeatable. Voice cloning, if used, is owner-consent only. Trust
Score is advisory (a decision aid for the shopkeeper), not an automated
lending decision — real lending would need consent + regulation work.

## 11. LIMITATIONS (own them before they're found — this builds trust)

- Single shopkeeper per deployment (multi-tenant is trivial schema work).
- Rule engine understands a bounded set of Hinglish patterns; Evon widens this
  but prompt-hardening for adversarial input is future work.
- Sentiment is keyword-based (a real model is roadmap).
- No real telephony in the demo — by design (DPDP + repeatability); production
  path is Gnani's Agent Builder platform / telephony partner.
- Anti-spoofing on the voice lock is basic.

## 12. ROADMAP

Before Nov 10: Gnani-mode switch + video (script ready), second language
(Marathi/Tamil), noise WER chart, 60s video polish.
Vision: real telephony out-dial → UPI links spoken into calls → customer
self-service line → trust score becomes a credit marketplace signal for NBFC
partners → inventory reorder by voice → WhatsApp channel with the same brain.
Framing: **"a voice-first financial operating system for micro-retail.
Bookkeeping is the wedge, collections is the revenue, credit data is the moat."**
