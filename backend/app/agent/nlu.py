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
    if any(ch in _TAMIL_CONS or ch in _TAMIL_VOWELS for ch in text):
        return _translit_tamil(text)
    if any(ch in _DEV for ch in text):
        return "".join(_DEV.get(ch, ch) for ch in text)
    return text


# Tamil script: consonants carry an inherent 'a'; ் (pulli) kills it; matras
# replace it. Fuzz-collapsing then yields 'rajesh' from ராஜேஷ் etc.
_TAMIL_CONS = {
    "க": "k", "ங": "ng", "ச": "ch", "ஞ": "nj", "ட": "t", "ண": "n", "த": "t",
    "ந": "n", "ப": "p", "ம": "m", "ய": "y", "ர": "r", "ல": "l", "வ": "v",
    "ழ": "zh", "ள": "l", "ற": "r", "ன": "n", "ஜ": "j", "ஷ": "sh", "ஸ": "s",
    "ஹ": "h", "ஃ": "h",
}
_TAMIL_VOWELS = {
    "அ": "a", "ஆ": "aa", "இ": "i", "ஈ": "ii", "உ": "u", "ஊ": "uu",
    "எ": "e", "ஏ": "ee", "ஐ": "ai", "ஒ": "o", "ஓ": "oo", "ஔ": "au",
}
_TAMIL_MATRA = {
    "ா": "aa", "ி": "i", "ீ": "ii", "ு": "u", "ூ": "uu", "ெ": "e",
    "ே": "ee", "ை": "ai", "ொ": "o", "ோ": "oo", "ௌ": "au",
}
_TAMIL_DIGITS = {"௦": "0", "௧": "1", "௨": "2", "௩": "3", "௪": "4", "௫": "5",
                 "௬": "6", "௭": "7", "௮": "8", "௯": "9"}


def _translit_tamil(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch == "்":
            if out and out[-1].endswith("a") and len(out[-1]) > 1:
                out[-1] = out[-1][:-1]
        elif ch in _TAMIL_MATRA:
            if out and out[-1].endswith("a") and len(out[-1]) > 1:
                out[-1] = out[-1][:-1]
            out.append(_TAMIL_MATRA[ch])
        elif ch in _TAMIL_CONS:
            out.append(_TAMIL_CONS[ch] + "a")
        elif ch in _TAMIL_VOWELS:
            out.append(_TAMIL_VOWELS[ch])
        elif ch in _TAMIL_DIGITS:
            out.append(_TAMIL_DIGITS[ch])
        else:
            out.append(_DEV.get(ch, ch))
    return "".join(out)


def fuzz(token: str) -> str:
    """Collapse doubled vowels so 'raajesh'~'rajesh', 'sharmaa'~'sharma'."""
    t = token.lower().strip(".,?!।")
    return re.sub(r"([a-z])\1{1,}", r"\1", t)


def skeleton(token: str) -> str:
    """Vowel-stripped consonant skeleton: 'varma'~'verma'~'vrma' all -> 'vrm'.
    Cross-script name matching needs this looseness (வர்மா -> varma)."""
    return re.sub(r"[aeiou]", "", fuzz(token))


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

# Marathi (Devanagari) — don/pannas/shambhar...
NUM_WORDS_MR = {
    "ek": 1, "don": 2, "teen": 3, "char": 4, "pach": 5, "saha": 6, "sat": 7,
    "aath": 8, "nau": 9, "dah": 10, "vis": 20, "tehs": 30, "chalis": 40,
    "pannas": 50, "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90,
    "shambhar": 100,
}

# Tamil — common romanizations + our-transliteration forms
NUM_WORDS_TA = {
    "onnu": 1, "ondru": 1, "irandu": 2, "irantu": 2, "moondru": 3, "moontu": 3,
    "naangu": 4, "naanku": 4, "ainthu": 5, "andhu": 5, "aaru": 6, "ezhu": 7,
    "ettu": 8, "onpathu": 9, "paththu": 10, "pattu": 10, "irupathu": 20,
    "irupatu": 20, "muppathu": 30, "naarpathu": 40, "aimpathu": 50,
    "aabathu": 60, "ezhabathu": 70, "embathu": 80, "thonnooru": 90,
    "nooru": 100,
}

MULT_100 = {"sau", "hundred", "shambhar", "she", "nooru"}
MULT_1000 = {"hazaar", "hajar", "thousand", "aayiram", "ayiram", "hijar"}
MULT_100K = {"lakh", "laakh", "latcham", "laksham"}

LANG_NUM_WORDS = {
    "hi": NUM_WORDS,
    "mr": {**NUM_WORDS, **NUM_WORDS_MR},
    "ta": {**NUM_WORDS, **NUM_WORDS_TA},
}


def parse_amount(text: str, lang: str = "hi-IN") -> float | None:
    """'₹2,500' / '2500' / 'do hazaar paanch sau' / 'don hajar' / 'irandu aayiram'.
    Date-fragments ('19 October', '15 tareekh') are stripped first so a date
    day-number is never read as an amount. Prisma's ITN usually returns digits,
    which this takes directly."""
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
        if any(w in tail for w in MULT_100K):
            val *= 100000
        elif any(w in tail for w in MULT_1000):
            val *= 1000
        return val

    words = t.split()
    num_words = LANG_NUM_WORDS.get(lang[:2], NUM_WORDS)
    total, current, seen_num = 0.0, 0.0, False
    for w in words:
        w = w.strip(".,?!")
        if w in ("dhai",):
            current, seen_num = 2.5, True
        elif w in ("dedh",):
            current, seen_num = 1.5, True
        elif w in MULT_100:
            if not seen_num:
                current = 1.0
            total += (current or 1) * 100
            current, seen_num = 0.0, False
        elif w in MULT_1000:
            total += (current or 1) * 1000
            current, seen_num = 0.0, False
        elif w in MULT_100K:
            total += (current or 1) * 100000
            current, seen_num = 0.0, False
        elif w in num_words:
            current += num_words[w]
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
    # skeleton pass: 'varma' in text ~ 'Verma' in ledger
    t_skel = re.sub(r"[^a-z ]", "", t_fuzz)
    skel_words = [skeleton(w) for w in t_skel.split()]
    for name in known_names:
        for tok in name.lower().split():
            st = skeleton(tok)
            if len(st) >= 3 and st in skel_words:
                return name
    m = re.search(r"(?:^|\s)([a-z\u0900-\u097F]{2,15}(?:\s(?:ji|bhai|bhaiya|seth|sahab))?)\s+(?:ko|ne|se|ka|ki|kaa)\b", t)
    if m:
        return m.group(1).title()
    return ""


INTENT_PATTERNS = [
    ("PAYMENT", [r"\b(diya|diye|de diya|jama hua|jama kiya|payment (aa|aaya|received)|paisa (de|diya))\b"]),
    ("QUERY_BALANCE", [r"\b(kitna (baki|baaki|udhaar|udhar)|baki kitna|kitna dena|balance (kya|kitna)|ka kitna)\b"]),
    ("SETTLE", [r"\b(hisaab (barabar|clear|puraa|pura|poora|settle)|settle (kar|kar do)|mast kar do)\b"]),
    ("BRIEFING", [r"\b(aaj ka hisaab|briefing|summary|din kaisa|report|subah ki)"]),
    ("TOTALS", [r"\b(total|kitna (udhaar|udhar) (bana|bana total|hua)|grand total|aaj ka total)"]),
    ("LIST_DUES", [r"\b(kin(ka|ke) udhaar|kis-kis ka|kis kis ka|due list|kaun(ka|se) baki)"]),
    ("SCORE", [r"\b(score|bharaut|bharosa|trust)\b"]),
]

# 'udhaar' alone must not mean ADD — a verb (lagana/likhna) or amount+'ko' is
# required, else 'kitna udhaar hai' would misclassify.
ADD_VERBS = {
    "hi": r"(laga|lagana|likh|likhna|jod|maar|add)",
    "mr": r"(lava|lavane|liha|lihi|jod|add)",
    "ta": r"(pativu|seyya|chey|serka|add)",
}

MR_PATTERNS = [
    ("PAYMENT", [r"\b(dile|dila|paisa dile|pay)\b"]),
    ("QUERY_BALANCE", [r"(kiti|ethake|kiti).*(bak|udh|udar)"]),
    ("SETTLE", [r"(hisheb (barobar|clear|pura)|settle)"]),
    ("TOTALS", [r"(aajcha|ekun|total)"]),
    ("BRIEFING", [r"(hisheb|briefing|summary)"]),
    ("SCORE", [r"(score|bharosa|trust)"]),
]

TA_PATTERNS = [
    ("PAYMENT", [r"(kodut|kotut|kotu|kudut|thanth|pay)"]),
    ("QUERY_BALANCE", [r"(evva|etthana|paththav|appa).*(paakk|pakk|bak|kad)"]),
    ("QUERY_BALANCE", [r"(paakk|pakk)"]),
    ("SETTLE", [r"(kanakku (clear|mudiyum)|settle)"]),
    ("TOTALS", [r"(inraiya|inru|total|mottam)"]),
    ("BRIEFING", [r"(kanakku|briefing|summary)"]),
    ("SCORE", [r"(score|nambikkai|trust)"]),
]

LANG_PATTERNS = {"hi": INTENT_PATTERNS, "mr": MR_PATTERNS, "ta": TA_PATTERNS}

LANG_UDHAAR_WORDS = {
    "hi": r"(udhaar|udhar|baki (likh|lagh)|(khata me (lag|likh)))",
    "mr": r"(udh|udar|khayat)",
    "ta": r"(kata|kadan|kadai|kadn|kaduil)",
}

ITEM_HINTS = re.compile(
    r"\b(chai|chini|cheeni|atta|aata|dal|chawal|rice|tel|sabun|masala|namak|doodh|milk|"
    r"biscuit|biscuits|ghee|supply|saman|kirana)\b",
    re.IGNORECASE,
)


def classify(text: str, lang: str = "hi-IN") -> str:
    t = text.lower()
    L = lang[:2] if lang else "hi"
    for intent, patterns in LANG_PATTERNS.get(L, INTENT_PATTERNS):
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                return intent
    # ADD needs udhaar-word + an action verb (or amount+'ko' below)
    if re.search(LANG_UDHAAR_WORDS.get(L, LANG_UDHAAR_WORDS["hi"]), t) \
            and re.search(ADD_VERBS.get(L, ADD_VERBS["hi"]), t, re.IGNORECASE):
        return "ADD_UDHAAR"
    if parse_amount(text, lang) and "ko" in t:
        return "ADD_UDHAAR"
    return "UNKNOWN"


def items_from(text: str) -> str:
    hits = ITEM_HINTS.findall(text)
    return ", ".join(sorted({h.lower() for h in hits}))
