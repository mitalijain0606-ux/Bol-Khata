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

# ---- Devanagari -> roman (for native-script transcripts) ----
# The cloud STT returns native-script text (ITN numerals included). The rule brain is
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
    "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "d", "ढ़": "dh", "फ़": "f",
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


_DEV_VIRAMA = "्"
_DEV_NUKTA = "़"
_DEV_NASAL = {"ं", "ँ"}
_DEV_MATRAS = set("ािीुूेैोौृॅॉ")
_DEV_VOWELS = set("अआइईउऊएऐओऔऋऑ")
_DEV_EXTRA = {"ृ": "ri", "ॅ": "e", "ॉ": "o", "ऑ": "o"}
_LABIALS = ("p", "b", "m")


def _dev_word(word: str) -> str:
    """One Devanagari word -> roman, with Hindi schwa handling.

    Consonants carry an inherent 'a' (शर्मा -> sharma, not shrma) that is dropped
    at the end of a word (हजार -> hajar) and in V-C-_-C-V position
    (कितना -> kitna, करना -> karna). Tokens: [roman, kind, has_schwa] where
    kind is C (consonant), V (vowel), N (nasal mark)."""
    toks: list[list] = []
    for ch in word:
        if ch == _DEV_NUKTA:
            continue
        if ch == _DEV_VIRAMA:
            if toks and toks[-1][1] == "C":
                toks[-1][2] = False
                toks[-1].append("halant")
            continue
        if ch in _DEV_NASAL:
            if toks and toks[-1][1] == "C" and toks[-1][2]:
                toks[-1][2] = "keep"      # schwa before a nasal mark is pronounced
            toks.append(["n", "N", False])
            continue
        if ch in _DEV_MATRAS:
            if toks and toks[-1][1] == "C":
                toks[-1][2] = False
            toks.append([_DEV_EXTRA.get(ch) or _DEV.get(ch, ""), "V", False])
            continue
        if ch in _DEV_VOWELS:
            toks.append([_DEV_EXTRA.get(ch) or _DEV.get(ch, ""), "V", False])
            continue
        r = _DEV.get(ch)
        if r is None or not ("\u0915" <= ch <= "\u0939" or "\u0958" <= ch <= "\u095f"):
            toks.append([r if r is not None else ch, "X", False])   # digits, punctuation
            continue
        toks.append([r, "C", True])

    cons = [i for i, t in enumerate(toks) if t[1] == "C"]
    # final schwa: dropped unless the word is a lone consonant or ends in a cluster (मित्र)
    if cons and cons[-1] == len(toks) - 1 and toks[-1][2] is True and len(toks) > 1:
        if not (len(toks[-2]) > 3 and toks[-2][3] == "halant"):
            toks[-1][2] = False
    # medial schwa: V C(a) C V -> V C C V
    for i in range(1, len(toks) - 1):
        t = toks[i]
        if t[1] != "C" or t[2] is not True:
            continue
        prev, nxt = toks[i - 1], toks[i + 1]
        prev_vowel = prev[1] == "V" or (prev[1] == "C" and prev[2])
        if prev[1] == "C" and len(prev) > 3:          # part of a consonant cluster
            continue
        nxt_voiced = nxt[1] == "C" and (
            nxt[2] or (i + 2 < len(toks) and toks[i + 2][1] == "V"))
        if prev_vowel and nxt_voiced:
            t[2] = False

    out = []
    for i, t in enumerate(toks):
        r = t[0]
        if t[1] == "N" and i + 1 < len(toks) and toks[i + 1][0][:1] in _LABIALS:
            r = "m"                                  # शंभर -> shambhar
        out.append(r + ("a" if t[1] == "C" and t[2] else ""))
    res = "".join(out)
    return {"sinh": "singh"}.get(res, res)


def _translit_dev(text: str) -> str:
    return re.sub(r"[\u0900-\u0963\u0966-\u097f]+", lambda m: _dev_word(m.group(0)), text) \
             .replace("।", ".").replace("॥", ".")


def transliterate(text: str) -> str:
    if any(ch in _TAMIL_CONS or ch in _TAMIL_VOWELS for ch in text):
        return _translit_tamil(text)
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return _translit_dev(text)
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


def canon(text: str) -> str:
    """Spelling-insensitive form used for intent + number matching, so the roman
    'hisaab / hazaar / teen' and the transliterated 'hisab / hajar / tin' agree."""
    t = text.lower().replace("ee", "i").replace("oo", "u")
    return re.sub(r"([a-z])\1+", r"\1", t)


def _canon_pattern(p: str) -> str:
    """canon() for a regex source — leaves escapes like \\b alone."""
    p = p.replace("ee", "i").replace("oo", "u")
    return re.sub(r"(?<!\\)([a-z])\1+", r"\1", p)


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

# spellings produced by transliterating Devanagari (छह -> chhah, छः -> chhah ...)
NUM_WORDS.update({"chhah": 6, "chah": 6, "che": 6, "tin": 3, "sat": 7, "ath": 8})


def _ck(d: dict) -> dict:
    return {canon(k): v for k, v in d.items()}


MULT_100 = {canon(w) for w in MULT_100}
MULT_1000 = {canon(w) for w in MULT_1000} | {"hazar", "hajar"}
MULT_100K = {canon(w) for w in MULT_100K}

LANG_NUM_WORDS = {
    "hi": _ck(NUM_WORDS),
    "mr": _ck({**NUM_WORDS, **NUM_WORDS_MR}),
    "ta": _ck({**NUM_WORDS, **NUM_WORDS_TA}),
}


def parse_amount(text: str, lang: str = "hi-IN") -> float | None:
    """'₹2,500' / '2500' / 'do hazaar paanch sau' / 'don hajar' / 'irandu aayiram'.
    Date-fragments ('19 October', '15 tareekh') are stripped first so a date
    day-number is never read as an amount. STT text normalization usually returns digits,
    which this takes directly."""
    t = canon(text.replace(",", "").replace("₹", " "))
    t = re.sub(r"\b(rupees|rupes|rupaye|rupay|rupae|rupe|rupaya|rs)\b\.?", " ", t)
    t = re.sub(
        r"\b\d{1,2}\s*(tarikh|october|november|december|january|february|march|"
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

    num_words = LANG_NUM_WORDS.get((lang or "hi")[:2], LANG_NUM_WORDS["hi"])
    words = [w.strip(".,?!") for w in t.split()]
    # Number words must sit next to each other ("do hazaar paanch sau"); a stray
    # 'do' in "likh do" / "kar do" is the verb, not a 2. Take the biggest run.
    best, run, in_run = 0.0, [0.0, 0.0, False], False

    def close():
        nonlocal best, run, in_run
        if in_run:
            best = max(best, run[0] + run[1])
        run, in_run = [0.0, 0.0, False], False

    for i, w in enumerate(words):
        prev = words[i - 1] if i else ""
        if w == "do" and prev in _DO_VERBS:
            close()
        elif w in ("dhai", "adhai"):
            run[1], run[2], in_run = 2.5, True, True
        elif w == "dedh":
            run[1], run[2], in_run = 1.5, True, True
        elif w in MULT_100:
            run[0] += (run[1] if run[2] else 1.0) * 100
            run[1], run[2], in_run = 0.0, False, True
        elif w in MULT_1000:
            run[0] += (run[1] or 1) * 1000
            run[1], run[2], in_run = 0.0, False, True
        elif w in MULT_100K:
            run[0] += (run[1] or 1) * 100000
            run[1], run[2], in_run = 0.0, False, True
        elif w in num_words:
            run[1] += num_words[w]
            run[2], in_run = True, True
        else:
            close()
    close()
    return best if best > 0 else None


# "<verb> do" = imperative ("likh do", "kar do"), not the number two
_DO_VERBS = {"likh", "kar", "laga", "de", "bata", "jod", "chadha", "dikha", "suna", "bana",
             "bhej", "hata", "mita", "rakh", "daal", "dal", "kliyar", "clear"}


def find_customer_name(text: str, known_names: list[str]) -> str:
    """Match a known customer name in the utterance — token-aware + vowel-fuzzy:
    'Sharma ji ko udhaar' matches 'Rajesh Sharma'; 'raajesh' matches 'Rajesh'
    (transliterations double vowels)."""
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
    if m and m.group(1).split()[0] not in _NOT_NAMES:
        return m.group(1).title()
    return ""


# words that sit before ko/ne/se/ka but are never a customer name
_NOT_NAMES = {
    "aaj", "aj", "kal", "parso", "kis", "kisi", "kiska", "kin", "sab", "sabka", "total",
    "udhaar", "udhar", "hisaab", "hisab", "paisa", "paise", "rupaye", "rupe", "baki",
    "baaki", "khata", "dukaan", "dukan", "din", "mahine", "hafte", "subah", "mujh",
    "is", "us", "in", "un", "kitna", "kitne", "payment", "cash", "score", "wada",
}


INTENT_PATTERNS = [
    ("PAYMENT", [r"\b(diya|diye|die|diy|de diya|jama|chukaya|chukaye|chuka diya|lautaya|lautaye|wapas (kiya|kiye|kar)|"
                 r"payment (aa|aaya|aayi|received|mila|mili)|paisa (de|diya)|(paise|rupaye|rupe) (aaye|aa gaye|mile|mil gaye))\b"]),
    ("QUERY_BALANCE", [r"\b(kitna (baki|baaki|udhaar|udhar)|baki kitna|kitna dena|balance (kya|kitna)|ka kitna)\b"]),
    ("SETTLE", [r"\b(hisaab (barabar|clear|kliyar|kliar|puraa|pura|poora|settle|setal)|khata (clear|kliyar|band|barabar)|"
                r"settle (kar|kar do)|setal kar|mast kar do)\b"]),
    ("BRIEFING", [r"\b(aaj ka hisaab|briefing|summary|din kaisa|report|subah ki)"]),
    ("TOTALS", [r"\b(total|kitna (udhaar|udhar) (bana|bana total|hua)|grand total|aaj ka total)"]),
    ("LIST_DUES", [r"\b(kin(ka|ke) udhaar|kis-kis ka|kis kis ka|due list|kaun(ka|se) baki)"]),
    ("SCORE", [r"\b(score|skor|bharaut|bharosa|trust|trast)\b"]),
]

# 'udhaar' alone must not mean ADD — a verb (lagana/likhna) or amount+'ko' is
# required, else 'kitna udhaar hai' would misclassify.
ADD_VERBS = {
    "hi": r"(laga|lagana|likh|likhna|jod|maar|chadha|add|\bed\b)",
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


def _compile(table):
    return [(intent, [re.compile(_canon_pattern(p), re.IGNORECASE) for p in pats])
            for intent, pats in table]


_COMPILED = {k: _compile(v) for k, v in LANG_PATTERNS.items()}
_UDHAAR_RE = {k: re.compile(_canon_pattern(v), re.IGNORECASE) for k, v in LANG_UDHAAR_WORDS.items()}
_VERB_RE = {k: re.compile(_canon_pattern(v), re.IGNORECASE) for k, v in ADD_VERBS.items()}
_TO_MARKER = re.compile(r"\b(ko|la|kku|ku)\b")   # Hindi ko / Marathi la / Tamil -kku


def classify(text: str, lang: str = "hi-IN") -> str:
    t = canon(text)
    L = lang[:2] if lang else "hi"
    if L not in _COMPILED:
        L = "hi"
    for intent, patterns in _COMPILED[L]:
        for p in patterns:
            if p.search(t):
                return intent
    # ADD needs udhaar-word + an action verb (or amount+'ko' below)
    if _UDHAAR_RE[L].search(t) and _VERB_RE[L].search(t):
        return "ADD_UDHAAR"
    if parse_amount(text, lang) and (_TO_MARKER.search(t) or _UDHAAR_RE[L].search(t)):
        return "ADD_UDHAAR"
    return "UNKNOWN"


def items_from(text: str) -> str:
    hits = ITEM_HINTS.findall(text)
    return ", ".join(sorted({h.lower() for h in hits}))
