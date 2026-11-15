# Narration script

Indian English with Hinglish examples. Each line starts at its time and should be
done by its end time (about 2.5 words a second). Captions for the demo scenes are
burnt into the video, so it also works muted (LinkedIn and X autoplay silently);
the number and story scenes carry their own on-screen text.

`narration.json` holds these timings; `add_narration.py` voices them with Gnani
Timbre and mixes them over the music.

| Start | End | Scene | Line |
|------:|----:|-------|------|
| 0:00.4 | 0:06.2 | Numbers | Every evening, in thirteen million kirana stores across India, the same old notebook comes out. |
| 0:06.6 | 0:12.4 | Numbers | Barely one shop in ten keeps its accounts digitally. The other nine still trust paper. |
| 0:12.6 | 0:18.2 | Numbers | And one in three customers buys on udhaar — take it today, pay later, on trust. |
| 0:18.4 | 0:23.8 | Numbers | Smudged names. Forgotten dues. Awkward reminders. Money already earned — that may never come home. |
| 0:24.2 | 0:33.6 | Idea | A shopkeeper with a queue at the counter has no time to type. He needs a khata that listens. So I built Bol-Khata. |
| 0:34.4 | 0:40.0 | Demo | Ramesh ne paanch sau rupaye udhaar liye. Done. Written to Ramesh's khata, balance read back. |
| 0:40.4 | 0:45.4 | Demo | Every customer has a complete khata — every entry, every promise, kept or broken. |
| 0:45.6 | 0:51.0 | Demo | When money comes back, just say so. The balance updates instantly. No pen, no maths. |
| 0:51.4 | 0:56.6 | Demo | A new customer? Just say their name, and their khata opens on its own. |
| 0:57.4 | 1:07.8 | Demo | This is the heart of it. The shopkeeper speaks naturally, in Hinglish. Gnani Prisma understands, the khata updates itself, and Gnani Timbre answers back, out loud. |
| 1:08.2 | 1:15.0 | Demo | Before giving credit, he can simply ask. Chauhan ji has already broken two promises — so, not today. |
| 1:15.6 | 1:20.6 | Demo | Sharma ji has always paid on time. Go ahead — he's good for it. |
| 1:21.4 | 1:36.6 | Demo | Every customer earns a trust score from how they actually pay. And when dues pile up, the agent makes the collection call itself — polite, patient, and it comes back with a date. In this demo, the customer is simulated. |
| 1:37.4 | 1:46.4 | Tech | Under the hood: Gnani Prisma listens, Gnani Timbre speaks, a reasoning model on Groq thinks — and a rule engine guards every rupee. |
| 1:47.6 | 1:59.4 | Impact | Thirteen million shopkeepers. No typing. No English menus. No forgotten udhaar. Just their own voice. Bol-Khata — your dukaan, your voice, your digital khata. |

## Sources for the numbers on screen

- **13 million kiranas, about 1.4 million digitised:** All India Consumer Products
  Distributors Federation (AICPDF), as reported by Storyboard18.
- **About 1 in 3 customers regularly buy on store credit:** Flourish Ventures with
  Bain & Company and 60 Decibels, a survey of kirana shoppers in India, Brazil,
  Egypt and Indonesia (about 33% regularly use store credit). It is a four-country
  figure, which is why the on-screen source names all four.
