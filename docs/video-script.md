# 60-Second Demo Video Script (Demo Day Drop award)

Phone se shoot karo (vertical), CapCut pe captions. Har shot ke saath bolna hai
(judge video mute bhi dekhe to captions se samajh aaye).

| # | Sec | Shot | Screen / Action | Caption |
|---|-----|------|-----------------|---------|
| 1 | 0–6 | Dukaan hook | Khata page, mic orb pe finger | "12 million kirana stores udhaar pe chalte hain. Lekin khata likhne ka time kise hai?" |
| 2 | 6–14 | Voice entry | Mic dabao → "Sharma ji ko do hazaar paanch sau ka udhaar lagana" → entry + reply bubble | "Bol do. Khata khud likh jaata hai — Hinglish, bolne wale tareeke me." |
| 3 | 14–20 | Query | "Verma ji ka kitna baki hai?" → jawab | "Sawal? Bas poochh lo." |
| 4 | 20–38 | THE CALL 🌟 | Calls → customer tap → call screen: agent opening → excuse → negotiation → result card "wada record ho gaya" | "Ye assistant nahi, EMPLOYEE hai. Khud call karta hai, bahane sunta hai, pakki date ka wada tulwaata hai — aur wada khata me likh jaata hai." |
| 5 | 38–46 | Bharaut-Score | Dashboard → kisi risky customer ka breakdown kholo | "Har customer ka Bharaut-Score — kaun pakka, kaun talne-wala. Wada toota to score girta hai." |
| 6 | 46–53 | Briefing | "▶ Sunao" dabao, briefing awaaz | "Roz subah AI manager ki briefing — aaj kisko call karna hai, kisne wada toda tha." |
| 7 | 53–60 | Closing | Ek shot: tota numbers overlay — "₹47,000 atka tha → ₹31,000 vasool" | "Bol-Khata. Khata ko awaaz di, awaaz ko yaaddasht, yaaddasht se ek credit manager banaya. Built on Gnani Prisma, Timbre, Evon." |

Post: LinkedIn/X pe `#GreatIndianAIInternshipChallenge #GnaniAI` — pinned comment me
tech breakdown (Prisma streaming + Evon tools + Timbre numerals + ECAPA voice lock).

## Interview ready answers (solo — sab khud explain kar sakte ho)

- **Flow ek entry ka:** mic → STT (Prisma/browser) → rule engine ya Evon tool-call →
  SQLite effect → confirmation → TTS (Timbre/browser).
- **Wada kaise record hota hai:** debtor persona state machine date bolta hai →
  Hinglish date parser (kal/parso/15 tareekh) → promise table → payment aaye to
  auto KEPT, due date guzar gayi to BROKEN → score me −25.
- **Privacy:** sab synthetic — Timbre/browser TTS se bana awaaz test set, fake numbers.
- **Latency:** streaming STT (~200ms P95 claim), tool-call <10ms (SQLite), TTS streaming —
  end-to-end conversational feel 1–1.5s.
