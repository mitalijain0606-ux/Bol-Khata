# Live Demo Run-Sheet (judges / LinkedIn live ke liye)

## Pehle se ready rakho
- [ ] Backend chalao: `cd backend && .venv/bin/uvicorn app.main:app --port 8000`
- [ ] Frontend built: `cd frontend && npm run build` (backend hi serve karta hai)
- [ ] DB seeded (fresh numbers ke liye): `.venv/bin/python -m scripts.seed_fake_data`
- [ ] Chrome kholo `http://localhost:8000` (ya phone pe tunnel URL + Add to Home Screen)
- [ ] Browser me mic permission pehle se allow karo (Settings → Site settings → Mic)
- [ ] Volume thasa ke — TTS awaaz sunai deni chahiye

## 5-minute live flow
1. **Khata tab** — mic dabao: "Sharma ji ko do hazaar ka udhaar lagana" → entry dikhao.
2. "Gupta ji ne paanch sau diye" → payment, balance ghatate dikhao.
3. "Aaj ka hisaab" → briefing line.
4. **Calls tab** — sabse pehle 😬 Talne-wala pe tap (excuse + push dikhega),
   phir 🤝 Bhav-taai-wala (partial payment + wada).
5. Result card dikhao: "Wada khata me record ho gaya."
6. **Hisaab tab** — usi customer ka score breakdown kholo ("Kyun 75? Wada toda −25").
7. Briefing ▶ Sunao — awaaz me poora din ka plan.
8. **Settings** — "Gnani Prisma/Timbre/Evon" providers card dikhao:
   "Ek config line pe poora stack Gnani pe switch ho jaata hai."

## Agar kuch fail ho (backup lines)
- Mic na chale: example buttons pe tap karo — "Text wala backup, awaaz wala main hai."
- TTS silent: bubbles padho — "silent server hai, phone pe awaaz aati hai."
- Koi API timeout: seed dobara chalao, fresh dukaan ready.

## Demo me mat bhoolna (pitch lines)
- "Ye assistant nahi, employee hai — poocha nahi jaata, kaam karta hai."
- "Sirf khata nahi — paisa wapas laata hai."
- "Sab data synthetic, DPDP-safe — fake customers, banavati awaazein."
- "Ek project, teen Gnani products ka use: Prisma (sunna), Evon (sochna), Timbre (bolna)."
