# Narration script

Indian English with Hinglish examples. Each line starts at its time and should be
done by its end time (about 2.5 words a second). Captions for the demo scenes are
burnt into the video, so it also works muted (LinkedIn and X autoplay silently);
the number and story scenes carry their own on-screen text.

`narration.json` holds these timings; `add_narration.py` voices them with Gnani
Timbre and mixes them over the music.

| Start | End | Scene | Line |
|------:|----:|-------|------|
| 0:00.6 | 0:06.2 | Numbers | India has thirteen million kirana stores. |
| 0:06.6 | 0:12.2 | Numbers | Only about one in ten keeps its books digitally. The rest run on a notebook. |
| 0:12.6 | 0:17.8 | Numbers | And one in three customers buys on udhaar — credit, on trust. |
| 0:18.2 | 0:23.6 | Numbers | Every rupee of it is written by hand, and chased in person. |
| 0:24.2 | 0:33.6 | Idea | So I asked: what if the shopkeeper could just say it? Bol-Khata — speak an entry, know before you lend, and let the agent collect. |
| 0:34.4 | 0:40.0 | Demo | Ramesh ne paanch sau rupaye udhaar liye. Written to Ramesh Mishra's khata, balance read back. |
| 0:40.4 | 0:45.2 | Demo | Every customer has a full khata, with a one-tap WhatsApp reminder. |
| 0:45.6 | 0:51.0 | Demo | Payments bring the balance down instantly. |
| 0:51.4 | 0:56.6 | Demo | And a new name simply opens a new khata — no forms. |
| 0:57.4 | 1:07.8 | Demo | Or just speak. Gnani Prisma turns speech into text, the agent updates the khata, and Gnani Timbre speaks the answer back. |
| 1:08.2 | 1:15.0 | Demo | Before lending, ask. Chauhan ji has broken two promises — so Bol-Khata says no. |
| 1:15.6 | 1:20.6 | Demo | Sharma ji always pays on time. Yes. |
| 1:21.4 | 1:36.6 | Demo | When money is overdue, the agent makes the collections call itself — politely agreeing a date and logging the promise. Here, with a simulated customer. |
| 1:37.4 | 1:46.4 | Tech | Gnani Prisma and Timbre for speech, GPT-OSS on Groq for reasoning, and a rule engine guarding every rupee. |
| 1:47.6 | 1:59.0 | Impact | Thirteen million counters. Each one can now just speak — no typing, no forgotten udhaar. Bol-Khata: your dukaan, your voice, your digital khata. |

## Sources for the numbers on screen

- **13 million kiranas, about 1.4 million digitised:** All India Consumer Products
  Distributors Federation (AICPDF), as reported by Storyboard18.
- **About 1 in 3 customers regularly buy on store credit:** Flourish Ventures with
  Bain & Company and 60 Decibels, a survey of kirana shoppers in India, Brazil,
  Egypt and Indonesia (about 33% regularly use store credit). It is a four-country
  figure, which is why the on-screen source names all four.
