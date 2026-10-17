# Mentor Meeting — Bol-Khata Pitch (15 min ka flow)

> Rule: pehle 2 minute me idea, phir LIVE DEMO (5 min), phir plan + sawal.
> Demo backup: docs/demo-run-sheet.md — mic na chale to example buttons.

---

## 1. Hook (30 second)

"Sir/Ma'am, main Gnani AI ke Great Indian AI Internship Challenge me participate kar
rahi hoon — India ka voice-AI company jo banks ke liye collections calls automate
karta hai. Deadline 10 November hai, aur 100 paid internships mil sakti hain, ₹1
lakh/month tak.

Mera project: **Bol-Khata** — kirana dukaandaar ka AI credit manager. Idea ek line me:
**dukaandaar bolke khata likhta hai, aur system khud customers ko call karke paise ka
wada tulwaata hai.** Sab data synthetic — fake customers, banavati awaazein — DPDP-safe."

## 2. Problem (1 minute)

Dukaandaar ki 2 problems hain, aur poora market sirf pehla solve kar raha hai:
1. **Khata likhna** — din bhar customers, likhne ka time nahi; entries chhoot jaati hain
2. **Paisa wapas laana** — yaad dilana awkward hai; "kal pakka" bolke log bhag jaate
   hain; kirana me ₹40–50,000 udhaar me atka rehta hai — aur aise customers ke paas
   CIBIL score bhi nahi, to dukaandaar ko pata bhi nahi kise udhaar dena chahiye

## 3. Solution — LIVE DEMO (5 minute)

App kholiye: http://localhost:8000 (Chrome)

1. **Bolke entry** — mic dabao: "Sharma ji ko do hazaar paanch sau ka udhaar" →
   entry ban jaati hai, Hinglish numbers parse hote hain
2. **Bolke sawaal** — "Verma ji ka kitna baki hai?" → turant jawab
3. **Vasooli call** ⭐ — due waale customer pe tap → agent khud call karta hai,
   excuse sunta hai, dabao daalta hai, **date ka wada leta hai** → result card:
   "wada record ho gaya" → khata me promise likh jaata hai
4. **Bharaut-Score** — har customer ka 0–100 score, breakdown ke saath (wada toda
   −25, der se diya −10...) → "Gupta ji ko 5000 aur dena chahiye?" ka jawab data se
5. **Subah ki briefing** — AI manager ka morning report, bolke sun sakta hai

## 4. Tech (1 minute, seedha)

- **Gnani ka poora stack** (challenge ki requirement): Prisma v2.5 STT (sunna),
  Timbre v2.5 TTS (bolna — 'Poorvi' Hinglish voice), Evon v3.3 LLM (sochna, tool-calling)
- Architecture: voice → STT → agent (tools: add_entry, query_dues, log_promise) →
  SQLite → TTS. FastAPI backend + React PWA (phone pe app jaisi)
- **Dual mode** — abhi mock mode me free chalta hai; Gnani keys aate hi ek .env line
  se poora stack Prisma/Timbre/Evon pe switch (endpoints exact wired hain)
- Voice-lock: sirf malik ki awaaz ledger badal sakti hai (Gnani ke ARMour ka angle)
- Status: **poora project built + tested hai** — 4 pages, call simulator, trust scores

## 5. Ye kyun jeetega (1 minute)

- 95% teams **assistant** banayengi (poochho-jawab do). Ye **employee** hai — khud
  kaam karta hai: call karta hai, wada tulwaata hai, follow-up karta hai
- Demo ka outcome **paisa** hai, feature nahi: "₹47,000 atka tha, system ne wade
  liye aur vasooli track hui"
- Gnani ka apna business collections hai — ye unka hi model unse pehle wali market
  (kirana) ke liye hai — interview me yahi pitch hai
- 6 award categories pe hit: Real Deal, Mixed Vibes, Jugaad, Demo Day Drop,
  Noise Canceller (WER test harness bana hai), Main Character (2nd language)

## 6. Plan + Mentor se kya maangna hai

- **Week-wise:** video teaser is hafte → Gnani Mode switch (key mil gayi hai) →
  2nd language (Marathi) + noise test report → final video + submit (10 Nov tak)
- **Mentor se puuchho:**
  1. "Idea me sabse kamzor link kya lagta hai?"
  2. "Demo me aur kya dikhaun to judges ko lage ki production soch hai?"
  3. "Trust Score ka formula aur simple/solid kaise ho?"

---

## Tough questions + short answers

**Q: Ye to khata apps (Khatabook) jaisa hai?**
A: Woh sirf pehli problem solve karte hain — likhna. Hum **paise wapas laate hain**
(collections agent) aur **credit decision** dete hain (Bharaut-Score). Khata input
hai, hamara output paisa hai.

**Q: Voice accuracy kaisi rahegi shor me?**
A: Prisma 14M hours telephony audio pe trained hai — noisy calls uska home ground
hai. Maine noise-test harness bhi banaya hai jo alag SNR pe WER naapta hai —
Numbers report ke saath dikhaungi.

**Q: Real calls kaise?**
A: Demo me 100% synthetic (challenge ka DPDP rule bhi yahi hai). Production me Gnani
ke Agent Builder platform / telephony partner se out-dial hoga — architecture already
us shape me hai.

**Q: Akela itna kaise?**
A: Scope control — core (voice khata + calls) pehle poora bana, advanced layers
(score, briefing, voice lock) uske baad. Har layer working state me hai, kuch bhi
aadha nahi.

**Q: Data safety?**
A: Zero real data. Fake naam/numbers, banavati awaazein. Ye challenge ka hard rule
hai aur maine ise feature banaya — "repeatably demonstrable" demo.
