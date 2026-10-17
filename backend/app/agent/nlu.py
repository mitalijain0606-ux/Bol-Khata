"""Hinglish NLU rule engine — the free, zero-dependency brain for Mock Mode.

Handles the spoken patterns of a dukaandaar:
  "Sharma ji ko do hazaar paanch sau ka udhaar lagana"
  "Sharma ji ne paanch sau diye"
  "Sharma ji ka kitna baki hai"
  "Sharma ji ka hisaab clear kar do"
  "aaj ka hisaab" / "kitna udhaar bana total"
Number words support: 0-99 + hazaar/thousand + lakh + sau/hundred combos.
"""
import re

from app.agent import tools as T

# ---- Devanagari -> roman (for Prisma transcripts) ----
# Prisma returns native-script text (ITN numerals included). The rule brain is
# roman-Hinglish, so we transliterate with a deliberate 'a'-friendly mapping:
# ा→a (not aa) keeps 'sharma' as 'sharma', 'udhaar' as 'udhaar'.
_DEV = {
    # consonants
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh",
    "स": "s", "ह": "h", "ळ": "l",
    "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f",
    # independent vowels (kept short to match ledger spellings)
    "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri",
    # matras & marks
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ं": "n", "ँ": "n", "ः": "h", "्": "", "़": "",
    # Devanagari digits -> ascii
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
    "।": ".", "॥": ".",
}


def transliterate(text: str) -> str:
    if not any(ch in _DEV for ch in text):
        return text
    return "".join(_DEV.get(ch, ch) for ch in text)


def fuzz(token: str) -> str:
    """Collapse doubled vowels so 'raajesh'~'rajesh', 'sharmaa'~'sharma'."""
    t = token.lower().strip(".,?!।")
    return re.sub(r"([a-z])\1{1,}", r"\1", t)


NUM_WORDS = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
    "cheh": 6, "chhe": 6, "satt": 7, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unnees": 19, "bees": 20,
    "ish": 21, "ikis": 21, "baais": 22, "teais": 23, "chaubees": 24, "pachchees": 25,
    "chhabbees": 26, "sattaais": 27, "atthaais": 28, "unattis": 29, "tees": 30,
    "ecchees": 31, "battees": 32, "aintees": 33, "chauntees": 34, "paintees": 35,
    "chhattees": 36, "saintees": 37, "adhtees": 38, "unchalees": 39, "chalees": 40,
    "talees": 41, "bayalees": 42, "taintalees": 43, "chauvalees": 44, "paintalees": 45,
    "chhayalees": 46, "saintalees": 47, "adhtalees": 48, "unachas": 49, "pachaas": 50,
    "ikyavan": 51, "baavan": 52, "tirpan": 53, "chauvan": 54, "pachpan": 55,
    "chhappan": 56, "sattaavan": 57, "atthaavan": 58, "unsath": 59, "saath": 60,
    "eksath": 61, "baasath": 62, "irsath": 63, "chausath": 64, "paisath": 65,
    "chhiyaasath": 66, "sarsath": 67, "adhsath": 68, "unhattar": 69, "sattar": 70,
    "ekhattar": 71, "bahattar": 72, "tihattar": 73, "chauhattar": 74, "pachhattar": 75,
    "chhihattar": 76, "sathattar": 77, "athhattar": 78, "unaasi": 79, "assi": 80,
    "ikyaasi": 81, "baraasi": 82, "tiraasi": 83, "chauraasi": 84, "pachaasi": 85,
    "chhiyaasi": 86, "sataasi": 87, "athhaasi": 88, "nauve": 89, "nabbe": 90,
    "ikyaanve": 91, "baanve": 92, "tiraanve": 93, "chauraanve": 94, "pachaanve": 95,
    "chhiyaanve": 96, "sattaanve": 97, "athaanve": 98, "ninyaanve": 99,
}


def parse_amount(text: str) -> float | None:
    """'₹2,500' / '2500' / 'do hazaar paanch sau' / 'paanch sau' / 'dhai sau'.
    Date-fragments ('19 October', '15 tareekh') are stripped first so a date
    day-number is never read as an amount."""
    t = text.lower().replace(",", "").replace("₹", "").replace("rupees", "").replace("rupaye", "")
    t = re.sub(
        r"\b\d{1,2}\s*(tareekh|tarikh|october|november|december|january|february|march|"
        r"april|june|july|august|september|oct|nov|dec|jan|feb|mar|apr|aug|sep)\b",
        " ", t,
    )

    m = re.search(r"\b(\d{2,9})\b", t)
    if m:  # digits present -> trust them (scaled by hazaar/lakh if adjacent)
        val = float(m.group(1))
        tail = t[m.end():m.end() + 10]
        if "lakh" in tail:
            val *= 100000
        elif "hazaar" in tail or "hajar" in tail or "thousand" in tail:
            val *= 1000
        return val

    words = t.split()
    total, current, seen_num = 0.0, 0.0, False
    for w in words:
        w = w.strip(".,?!")
        if w in ("dhai",):
            current, seen_num = 2.5, True
        elif w in ("dedh",):
            current, seen_num = 1.5, True
        elif w in ("sau", "hundred"):
            if not seen_num:
                current = 1.0
            total += (current or 1) * 100
            current, seen_num = 0.0, False
        elif w in ("hazaar", "hajar", "thousand"):
            total += (current or 1) * 1000
            current, seen_num = 0.0, False
        elif w == "lakh":
            total += (current or 1) * 100000
            current, seen_num = 0.0, False
        elif w in NUM_WORDS:
            current += NUM_WORDS[w]
            seen_num = True
    total += current
    return total if total > 0 else None


def find_customer_name(text: str, known_names: list[str]) -> str:
    """Match a known customer name in the utterance — token-aware + vowel-fuzzy:
    'Sharma ji ko udhaar' matches 'Rajesh Sharma'; 'raajesh' matches 'Rajesh'
    (Prisma transliterations double vowels)."""
    t = re.sub(r"\b(ji|bhai|bhaiya|seth|sahab)\b", "", text.lower())
    t_fuzz = fuzz(t)
    best, best_len = "", 0
    for name in known_names:
        for tok in name.lower().split():
            ftok = fuzz(tok)
            if len(ftok) > 2 and ftok in t_fuzz and len(ftok) > best_len:
                best, best_len = name, len(ftok)
    if best:
        return best
    m = re.search(r"(?:^|\s)([a-z\u0900-\u097F]{2,15}(?:\s(?:ji|bhai|bhaiya|seth|sahab))?)\s+(?:ko|ne|se|ka|ki|kaa)\b", t)
    if m:
        return m.group(1).title()
    return ""


INTENT_PATTERNS = [
    ("PAYMENT", [r"\b(diya|diye|de diya|jama hua|jama kiya|payment (aa|aaya|received)|paisa (de|diya))\b"]),
    ("ADD_UDHAAR", [r"\b(udhaar|udhar|baki (likh|lagh|khata)|(khata me (lag|likh)|(likh|lagh) (do|de|na))|credit)\b"]),
    ("QUERY_BALANCE", [r"\b(kitna (baki|baaki|udhaar|udhar|bakipada)|baki kitna|kitna dena|balance (kya|kitna)|ka kitna)\b"]),
    ("SETTLE", [r"\b(hisaab (barabar|clear|puraa|pura|poora|settle)|settle (kar|kar do)|mast kar do)\b"]),
    ("BRIEFING", [r"\b(aaj ka hisaab|briefing|summary|din kaisa|report|subah ki)"]),
    ("TOTALS", [r"\b(total|kitna (udhaar|udhar) (bana|bana total|hua)|grand total|aaj ka total)"]),
    ("LIST_DUES", [r"\b(kin(ka|ke) udhaar|kis-kis ka|kis kis ka|due list|kaun(ka|se) baki)"]),
    ("SCORE", [r"\b(score|bharaut|bharosa|trust)\b"]),
]

ITEM_HINTS = re.compile(
    r"\b(chai|chini|cheeni|atta|aata|dal|chawal|rice|tel|sabun|masala|namak|doodh|milk|"
    r"biscuit|biscuits|ghee|supply|saman|kirana)\b",
    re.IGNORECASE,
)


def classify(text: str) -> str:
    t = text.lower()
    # payment before udhaar (both may say 'likh do')
    for intent, patterns in INTENT_PATTERNS:
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                if intent == "ADD_UDHAAR" and re.search(r"\b(ne .*(diya|diye)|diya|diye|jama)\b", t) and "udhaar" not in t:
                    continue
                return intent
    if parse_amount(text) and "ko" in t:
        return "ADD_UDHAAR"
    return "UNKNOWN"


def items_from(text: str) -> str:
    hits = ITEM_HINTS.findall(text)
    return ", ".join(sorted({h.lower() for h in hits}))
