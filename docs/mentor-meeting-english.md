# Mentor Meeting Prep — Bol-Khata (English, in-depth)

> Structure: Idea (2 min) → Why this (1 min) → Live demo (5 min) → Features depth (3 min)
> → Roadmap (2 min) → Mentor asks (2 min). Total ~15 min.

---

## 1. THE IDEA (30-second pitch)

"I'm building **Bol-Khata** — an AI credit manager for India's kirana stores — for
Gnani AI's Great Indian AI Internship Challenge (deadline Nov 10; top entries get
up to 100 paid six-month internships, stipend up to ₹1 lakh/month).

The one-liner: **the shopkeeper speaks in Hinglish, the ledger writes itself, the
system calls customers on its own, negotiates repayment dates, and scores how
trustworthy each customer is — so the shopkeeper always knows who deserves credit.**

It's already fully built and working end-to-end. Let me show you."

## 2. THE PROBLEM (why this exists)

Kirana stores run on udhaar (informal credit). A typical store has ₹40,000–₹50,000
stuck in outstanding udhaar at any time. That creates three stacked problems:

1. **Bookkeeping friction** — the owner works 14-hour days with both hands busy.
   Opening an app and typing an entry mid-transaction doesn't happen. Entries get
   missed, amounts get forgotten, disputes start.
2. **Money recovery** — chasing repayments is awkward and slow. Customers say
   "kal pakka" and vanish. Nobody tracks promises vs. actual payments.
3. **Credit trust** — most of these customers have zero formal credit history.
   The shopkeeper decides "should I give Ramesh ₹5,000 more?" purely on memory
   and gut.

Existing apps (Khatabook, OkCredit) only solved problem #1 — digital bookkeeping.
**Problem #2 is where the actual money leaks, and #3 is what would unlock formal
lending for this segment. Nobody solves those by voice.**

Why voice as the interface:
- The shopkeeper's hands and eyes are busy — speech is the only free channel
- Shopkeepers already narrate transactions out loud ("Ramesh ko paanch sau ka
  saman, udhaar pe")
- Voice works across literacy levels
- India speaks code-mixed Hinglish, not English UI language

## 3. WHY I CHOSE THIS PROJECT

1. **It mirrors the host company's own business.** Gnani AI's core revenue is
   voice agents for collections and customer engagement in BFSI (their ASSIST,
   ATLAS analytics, and ARMour voice-biometrics products). Bol-Khata is the same
   collections-agent pattern applied to a market Gnani doesn't serve yet —
   12–13 million kirana stores. In an interview, this shows I understand their
   product market-fit, not just their APIs.
2. **It fits the challenge theme** — "Sovereign AI for India": an Indian problem,
   Indian language, code-mixed speech, real Indian audio conditions.
3. **It's demoable in 60 seconds** — the hackathon requires a public demo video
   with community engagement. A live voice negotiation with a fake debtor is
   inherently watchable; a chatbot is not.
4. **Solo-buildable in 4 weeks** — I scoped it so the core is done in week 1–2
   and advanced layers are additive. (In fact, the core is already complete.)
5. **Every feature forces depth on their stack** — streaming ASR, agent
   tool-calling, TTS numerals, speaker verification — so there's real engineering
   to talk about in the interview.

## 4. FEATURES (in depth — what each one does and why it matters)

**A. Voice-first ledger (the foundation)**
- Speak naturally: "Sharma ji ko do hazaar paanch sau ka udhaar lagana" → the
  system parses Hinglish number words (do hazaar paanch sau = ₹2,500), matches
  "Sharma ji" to "Rajesh Sharma" in the ledger (honorific- and token-aware name
  matching), and creates the entry.
- Conversational queries: "kitna baki hai", "aaj ka hisaab", "kis-kis ka udhaar".
- Every entry also stores the raw spoken sentence — an audit trail of what was
  actually said.

**B. Outbound collections agent (the differentiator)**
- The system proactively calls customers with overdue balances. The agent opens
  the call, listens to excuses, pushes back appropriately (harder if the customer
  broke a previous promise), and extracts a **promise-to-pay date** — which is
  written back into the ledger and tracked.
- Promise lifecycle: PENDING → KEPT (auto-settled when payment arrives) or
  BROKEN (on due-date pass) → feeds the trust score and future call tone.
- Demo implementation: three synthetic debtor personas (Pakka-wala who agrees
  fast, Talne-wala who deflects, Bhav-taai-wala who offers partial payment) —
  so the negotiation is fully repeatable on stage, with zero real phone numbers.

**C. Bharaut-Score (trust score)**
- Explainable formula per customer: start at 100; broken promise −25, late
  payment −10, 30+ day stale balance −5; each kept promise +5 (max +20).
- The UI shows the full breakdown — "why is this 75?" — because a shopkeeper
  will only trust a score he can audit. This also becomes the credit signal for
  formal lending later.

**D. Morning briefing (the "employee" feel)**
- A generated spoken summary every morning: total udhaar, today's cash, the
  nearest promise due, who broke a promise, the biggest outstanding balance,
  and how many calls to make. It shifts the product from assistant to employee.

**E. Voice lock (security layer)**
- Owner enrolls their voice (ECAPA-TDNN speaker embeddings, runs on CPU).
  Destructive actions — deleting or settling entries — only work with the
  owner's verified voice. Customers speaking near the counter can't touch the
  ledger. This mirrors Gnani's ARMour voice-biometrics line.

**F. Noise robustness (engineering credibility)**
- Kirana stores are loud. I built a test harness that generates synthetic speech,
  mixes market/traffic noise at different SNRs (0/5/10 dB), and measures WER —
  so I can show a quantified noise-robustness report, not a claim.

**G. Privacy by design**
- 100% synthetic data — fake names, fake numbers, synthesized voices. This
  complies with the challenge's DPDP rule and makes the demo infinitely
  repeatable.

## 5. WHAT'S ALREADY BUILT (status — the strongest slide)

- Full-stack working app: FastAPI backend + React PWA (installs like a phone app)
- Voice loop end-to-end, 4 screens (Khata, Calls, Dashboard, Settings)
- Collections call simulator with 3 personas, promise capture, call analytics
- Trust scores with breakdown UI, morning briefing, fake-data seeder
- **Dual-mode architecture**: currently runs in a free mock mode (zero credits);
  one line in `.env` switches STT/TTS/reasoning to Gnani Prisma v2.5, Timbre
  v2.5 (the "Poorvi" Hinglish voice), and Evon v3.3 with exact documented
  endpoints already wired. The final demo video will be shot in Gnani mode.
- Git-versioned, seeded with realistic fake data.

## 6. WHAT MORE CAN WE DO (roadmap)

**Before the deadline (Nov 10):**
- Second language (Marathi or Tamil) → "Main Character" low-resource award angle
- Publish the noise-robustness WER report as a chart
- Sharpen the 60-second demo video (script is ready)

**Post-challenge / product vision:**
- Real telephony out-dial via Gnani's Agent Builder platform or a telephony partner
- UPI payment links spoken into the call ("main link bhej raha hoon, abhi kar lo")
- Customer self-service: customers call in, hear their balance, get a payment link
- From trust score → a credit marketplace: partner NBFCs underwrite kirana udhaar
  using this repayment data (with consent) — this is the fintech endgame
- Inventory + reorder by voice ("atta khatam ho gaya, 10 bag laga do")
- WhatsApp/text fallback channel with the same brain (omnichannel, like Gnani's stack)
- Multi-shop wholesale groups: a kirana owner is also a borrower from distributors —
  both sides of the ledger

**The 10-year framing:** "a voice-first financial operating system for micro-retail."
Bookkeeping is the wedge, collections is the revenue, credit data is the moat.

## 7. WHAT HELP I WANT FROM YOU (concrete asks)

1. **Stress-test the weakest link** — where do you think this breaks: voice
   accuracy in noise, the collections negotiation quality, or the trust score's
   usefulness? I want to over-invest in the right layer.
2. **A judge's dry run** — in week 3, can you watch my 2-minute demo and tell me
   what a hiring judge would poke at? One dry run from you is worth a week of my
   guessing.
3. **Prioritization** — with ~3.5 weeks left and solo capacity, help me rank:
   second language vs. noise report vs. deeper analytics vs. polish.
4. **Domain sanity-check** — does the collections flow sound realistic for actual
   kirana dynamics? Anything about repayment culture I'm getting wrong?
5. **User-contact if possible** — even 2–3 conversations with real shopkeepers
   (or anyone who runs a counter business) would ground my claims. If you know
   anyone, a 10-minute intro would help.
6. **Metrics that make it credible** — what numbers should I measure and show
   (WER at SNR, promise-kept rate, recovery rate) so the demo reads as
   engineering, not theater?

## 8. LIKELY QUESTIONS & SHORT ANSWERS

**Q: How is this different from Khatabook?**
A: Khatabook digitized the notebook — input. We attack the output side: recovery
and credit decisions. Same records, but ours make phone calls and score trust.

**Q: Will voice actually work in a noisy shop?**
A: Prisma is trained on 14M hours of telephonic audio — noise is its home turf.
And I'm not asking anyone to trust a claim: I built a WER-vs-SNR benchmark to
quantify it, and I'll show the chart.

**Q: Is calling customers legal/ethical?**
A: The demo is 100% synthetic — no real numbers, per the challenge's DPDP rule.
Production would need explicit consent at enrollment + TRAI DLT registration for
out-dial, which is standard for any collections system.

**Q: You're solo — is this too much?**
A: I scoped ruthlessly: voice ledger + collections core first, advanced layers
after. Everything currently shown is already built and tested; the remaining
weeks are polish and the Gnani-mode switch, not new architecture.

**Q: What if the judges have seen voice assistants already?**
A: Assistants answer when asked. This initiates — it calls, negotiates, records
promises, and follows up. The demo's outcome is recovered money, not a clever
reply. That's also literally Gnani's collections business pointed at a new market.

**Q: What's your tech stack?**
A: FastAPI + SQLite backend, React PWA frontend, WebSockets for streaming voice.
Gnani Prisma (STT), Timbre (TTS), Evon (reasoning + tool-calling). SpeechBrain
ECAPA-TDNN for speaker verification. A deterministic Hinglish NLU engine as the
free fallback brain, with Evon tool-calling as the production brain.
