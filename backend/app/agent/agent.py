"""The agent brain: LLM tool-calling when configured, Hinglish rule engine otherwise.

Both paths produce the same shape:
  {"reply": str, "action": str, "data": {...}}  — frontend speaks `reply`.
"""
import json
import logging
import re
import time

from app.agent import nlu, tools as T
from app.analytics import trust_score
from app.db import db
from app.speech import evon
from app.speech.stt import ProviderNotConfigured

log = logging.getLogger("bolkhata.agent")

TOOL_SCHEMA = [
    {
        "name": "add_entry",
        "description": "Khata me UDHAAR (customer ne saman udhaar pe liya) ya PAYMENT (customer ne paisa diya) ki entry add karo.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "kind": {"type": "string", "enum": ["UDHAAR", "PAYMENT"]},
                "amount": {"type": "number"},
                "items_text": {"type": "string"},
            },
            "required": ["customer_name", "kind", "amount"],
        },
    },
    {
        "name": "query_balance",
        "description": "Ek customer ka total bakipada (balance) batao.",
        "parameters": {
            "type": "object",
            "properties": {"customer_name": {"type": "string"}},
            "required": ["customer_name"],
        },
    },
    {
        "name": "totals_today",
        "description": "Aaj ka total: kitna udhaar bana, kitna cash aaya.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_dues",
        "description": "Jin customers ka udhaar baki hai unki list.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "briefing",
        "description": "Subah/salary-time ki poore din ki briefing.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "trust_score",
        "description": "Ek customer ka bharaut-score aur uska breakdown.",
        "parameters": {
            "type": "object",
            "properties": {"customer_name": {"type": "string"}},
            "required": ["customer_name"],
        },
    },
]

TOOL_FNS = {"add_entry", "query_balance", "totals_today", "list_dues", "briefing", "trust_score"}


def run_tool(name: str, args: dict, transcript: str = "", sid: int = 1) -> dict:
    with db() as conn:
        if name == "add_entry":
            kind = str(args.get("kind") or "UDHAAR").upper()
            try:
                amount = float(args.get("amount") or 0)
            except (TypeError, ValueError):
                amount = 0.0
            cname = args.get("customer_name", "")
            # a payment never invents a customer; an udhaar entry may
            cust = (T.find_customer(conn, cname, sid) if kind == "PAYMENT"
                    else T.find_or_create_customer(conn, cname, shopkeeper_id=sid))
            if not cust or amount <= 0 or kind not in ("UDHAAR", "PAYMENT"):
                return {"reply": "Customer ka naam ya amount clear nahi tha — dobara boliye.",
                        "action": "NEED_AMOUNT", "data": {}}
            args = {**args, "kind": kind, "amount": amount}
            T.add_entry(conn, cust["id"], kind, amount, args.get("items_text", ""), transcript, shopkeeper_id=sid)
            if kind == "PAYMENT":
                T.settle_due_promises(conn, cust["id"], amount)
            bal = T.customer_balance(conn, cust["id"])
            kind_word = "udhaar lagaya" if args.get("kind") == "UDHAAR" else "paisa jama kiya"
            return {
                "reply": f"Theek hai — {cust['name']} ne {T.fmt_money(float(args['amount']))} ka {kind_word}. "
                         f"Ab tak ka total bakipada {T.fmt_money(bal)} hai.",
                "action": "ENTRY_ADDED",
                "data": {"customer": cust["name"], "amount": float(args["amount"]),
                         "kind": args.get("kind"), "balance": bal},
            }
        if name == "query_balance":
            cust = T.find_customer(conn, args.get("customer_name", ""), sid)
            if not cust:
                return {"reply": "Ye customer khata me nahi mila. Naam phir se boliye.", "action": "NOT_FOUND", "data": {}}
            bal = T.customer_balance(conn, cust["id"])
            return {"reply": f"{cust['name']} ka total bakipada {T.fmt_money(bal)} hai.",
                    "action": "BALANCE", "data": {"customer": cust["name"], "balance": bal}}
        if name == "totals_today":
            return _totals_reply(conn, "hi-IN", sid)
        if name == "list_dues":
            dues = [c for c in T.customers_with_dues(conn, sid) if c["balance"] > 0]
            if not dues:
                return {"reply": "Aaj sab ka hisaab clear hai — kisi ka udhaar nahi!", "action": "LIST_DUES", "data": []}
            names = ", ".join(f"{c['name']} {T.fmt_money(c['balance'])}" for c in dues[:8])
            return {"reply": f"Ye logon ka udhaar baki hai: {names}.", "action": "LIST_DUES", "data": dues}
        if name == "briefing":
            from app.analytics.briefing import build_briefing
            return build_briefing(conn, sid)
        if name == "trust_score":
            cust = T.find_customer(conn, args.get("customer_name", ""), sid)
            if not cust:
                return {"reply": "Ye customer khata me nahi mila.", "action": "NOT_FOUND", "data": {}}
            T.expire_promises(conn, sid)
            res = trust_score.compute(conn, cust["id"])
            return {"reply": f"{cust['name']} ka bharaut-score {res['score']}/100 hai. {res['one_liner']}",
                    "action": "TRUST_SCORE", "data": res}
    return {"reply": "Samajh nahi aaya, dobara boliye.", "action": "UNKNOWN", "data": {}}


# ---------------- rule-engine path (local brain) ----------------

# Replies for Marathi / Tamil in native script (the TTS speaks them natively).
REPLIES = {
    "mr-IN": {
        "add": "{name} वर {amt} ची नोंद लावली. एकूण बाकी {bal}.",
        "pay": "नोंद झाली — {name} चे {amt} पेमेंट. बाकी आता {bal}.",
        "balance": "{name} ची एकूण बाकी {amt} आहे.",
        "totals": "आजचा उधार {u}, रोख आली {c}. एकूण उधार {t}.",
        "need_amount": "कितीचा उधार लावायचा? रक्कम सांगा.",
        "need_name": "कोणाच्या नावावर लिहायची? नाव सांगा.",
        "not_found": "{name} खात्यात नाही.",
        "settled": "{name} चा हिशेब पूर्ण क्लिअर — {amt} सेटल.",
        "unknown": "समजले नाही, पुन्हा सांगा.",
    },
    "ta-IN": {
        "add": "{name} க்கு {amt} கடன் பதிவு செய்யப்பட்டது. மொத்த பாக்கி {bal}.",
        "pay": "பதிவு ஆனது — {name} {amt} செலுத்தினார். பாக்கி இப்போது {bal}.",
        "balance": "{name} மொத்த பாக்கி {amt}.",
        "totals": "இன்றைய கடன் {u}, வரவு {c}. மொத்த கடன் {t}.",
        "need_amount": "எவ்வளவு கடன் சேர்க்கவேண்டும்? தொகையை சொல்லுங்கள்.",
        "need_name": "யார் பெயரில் எழுதவேண்டும்? பெயரை சொல்லுங்கள்.",
        "not_found": "{name} கணக்கில் இல்லை.",
        "settled": "{name} கணக்கு முழுவதும் முடிந்தது — {amt} செலுத்தப்பட்டது.",
        "unknown": "புரியவில்லை, மீண்டும் சொல்லுங்கள்.",
    },
}


def _reply(lang: str, key: str, **kw) -> str:
    tpl = REPLIES.get(lang, {}).get(key)
    return tpl.format(**kw) if tpl else ""


def _totals_reply(conn, lang: str, sid: int) -> dict:
    tot = T.totals(conn, sid)
    u, c, t = (T.fmt_money(tot["udhaar_today"]), T.fmt_money(tot["cash_in_today"]),
               T.fmt_money(tot["outstanding"]))
    reply = _reply(lang, "totals", u=u, c=c, t=t) or (
        f"Aaj ka udhaar {u} bana, cash aaya {c}. Kul baki udhaar abhi {t} par hai.")
    return {"reply": reply, "action": "TOTALS", "data": tot}


# A settle wipes a whole balance, so it is a two-step: the agent asks, the owner
# says "haan". Pending confirmations live here per shopkeeper for 60 seconds.
_PENDING_SETTLE: dict[int, tuple[int, float]] = {}
_YES = re.compile(r"^(ji )?(han|ha|haa|yes|ok|okay|pakka|bilkul|thik hai|kar do|kardo|kar de|ho|hoy|ama|am|sari)\b")
_NO = re.compile(r"^(ji )?(nahi|nahin|na|no|mat|cancel|rehne do|ruk|nako|venda|vendam)\b")


def _do_settle(conn, cust, raw: str, lang: str, sid: int) -> dict:
    bal = T.customer_balance(conn, cust["id"])
    if bal <= 0:
        return {"reply": f"{cust['name']} ka hisaab pehle se clear hai — kuch baki nahi.",
                "action": "BALANCE", "data": {"customer": cust["name"], "balance": bal}}
    T.add_entry(conn, cust["id"], "PAYMENT", bal, "hisaab clear", raw, shopkeeper_id=sid)
    T.settle_due_promises(conn, cust["id"], bal)
    reply = _reply(lang, "settled", name=cust["name"], amt=T.fmt_money(bal))
    return {"reply": reply or f"{cust['name']} ka hisaab poora clear — {T.fmt_money(bal)} settle.",
            "action": "SETTLED", "data": {"customer": cust["name"], "balance": 0.0}}


def _lend_advice(conn, name: str, amount: float | None, sid: int) -> dict:
    """'Sharma ji ko 2000 udhaar du?' -> a yes / careful / no backed by the score."""
    cust = T.find_customer(conn, name, sid)
    ask = f"{T.fmt_money(amount)} " if amount else ""
    if not cust:
        return {"reply": f"{name} naya customer hai — khata me koi history nahi. "
                         "Chhote udhaar se shuru kijiye, phir score banega.",
                "action": "LEND_ADVICE", "data": {"decision": "careful", "customer": name}}
    T.expire_promises(conn, sid)
    res = trust_score.compute(conn, cust["id"])
    bal, score, b = res["balance"], res["score"], res["breakdown"]
    facts = f"Score {score}/100, abhi {T.fmt_money(bal)} baki hai"
    if b["promises_broken"]:
        facts += f", {b['promises_broken']} wada toda hai"
    elif b["promises_kept"]:
        facts += f", {b['promises_kept']} wade poore kiye hain"
    after = f" Dene ke baad total {T.fmt_money(bal + amount)} ho jayega." if amount else ""
    if score >= 80:
        decision, line = "yes", f"Haan, {cust['name']} ko {ask}udhaar de sakte hain."
    elif score >= 55:
        decision, line = "careful", (f"{cust['name']} ko {ask}udhaar sambhal ke dijiye — "
                                     "chhota udhaar theek hai, bada nahi.")
    else:
        decision, line = "no", (f"Nahi — {cust['name']} ko abhi {ask}udhaar mat dijiye. "
                                "Pehle purana baki clear karwaiye.")
    return {"reply": f"{line} {facts}.{after}", "action": "LEND_ADVICE",
            "data": {"decision": decision, "customer": cust["name"], "customer_id": cust["id"],
                     "score": score, "balance": bal, "amount": amount}}


def _undo_last(conn, sid: int) -> dict:
    last = conn.execute(
        """SELECT e.*, c.name AS customer_name FROM entry e JOIN customer c ON c.id = e.customer_id
           WHERE e.shopkeeper_id = ? ORDER BY e.id DESC LIMIT 1""", (sid,)).fetchone()
    if not last:
        return {"reply": "Khata me hatane ke liye koi entry nahi hai.", "action": "UNKNOWN", "data": {}}
    conn.execute("DELETE FROM entry WHERE id = ?", (last["id"],))
    kind = "udhaar" if last["type"] == "UDHAAR" else "payment"
    bal = T.customer_balance(conn, last["customer_id"])
    return {"reply": f"Hata diya — {last['customer_name']} ki {T.fmt_money(last['amount'])} ki {kind} entry. "
                     f"Ab bakipada {T.fmt_money(bal)}.",
            "action": "ENTRY_DELETED",
            "data": {"customer": last["customer_name"], "amount": last["amount"], "balance": bal}}


def rule_reply(text: str, lang: str = "hi-IN", sid: int = 1) -> dict:
    raw = text                      # audit trail keeps exactly what was spoken
    text = nlu.transliterate(text)  # STT transcripts arrive in native scripts

    pending = _PENDING_SETTLE.pop(sid, None)
    if pending and time.time() - pending[1] < 60:
        said = nlu.canon(text).strip(" .,!?")
        if _YES.search(said):
            with db() as conn:
                cust = conn.execute("SELECT * FROM customer WHERE id = ? AND shopkeeper_id = ?",
                                    (pending[0], sid)).fetchone()
                if cust:
                    return _do_settle(conn, cust, raw, lang, sid)
        elif _NO.search(said):
            return {"reply": "Theek hai, kuch nahi badla.", "action": "CANCELLED", "data": {}}
        # anything else: forget the pending settle and treat it as a new command

    intent = nlu.classify(text, lang)
    amount = nlu.parse_amount(text, lang)
    native = lang in REPLIES  # Marathi/Tamil reply in native script for the voice
    with db() as conn:
        known = [r["name"] for r in conn.execute(
            "SELECT name FROM customer WHERE shopkeeper_id = ?", (sid,)).fetchall()]
        name = nlu.find_customer_name(text, known)

        if intent == "PAYMENT":
            if not amount:
                return {"reply": _reply(lang, "need_amount") or "Kitne ka payment aaya? Amount bol dijiye.",
                        "action": "NEED_AMOUNT", "data": {}}
            if not name:
                return {"reply": _reply(lang, "need_name") or "Kis customer ne diye? Naam bhi bol dijiye.",
                        "action": "NEED_NAME", "data": {}}
            cust = T.find_customer(conn, name, sid)
            if not cust:
                return {"reply": _reply(lang, "not_found", name=name) or
                                 f"{name} khata me nahi hai — pehle unka udhaar likhiye.",
                        "action": "NOT_FOUND", "data": {}}
            T.add_entry(conn, cust["id"], "PAYMENT", amount, nlu.items_from(text), raw, shopkeeper_id=sid)
            T.settle_due_promises(conn, cust["id"], amount)
            bal = T.customer_balance(conn, cust["id"])
            reply = _reply(lang, "pay", name=cust["name"], amt=T.fmt_money(amount), bal=T.fmt_money(bal))
            return {"reply": reply or f"Note ho gaya — {cust['name']} ka payment {T.fmt_money(amount)}. "
                                     f"Bakipada ab {T.fmt_money(bal)}.",
                    "action": "ENTRY_ADDED",
                    "data": {"customer": cust["name"], "amount": amount, "kind": "PAYMENT", "balance": bal}}

        if intent == "ADD_UDHAAR":
            if not amount:
                return {"reply": _reply(lang, "need_amount") or "Kitne ka udhaar lagana hai? Amount boliye.",
                        "action": "NEED_AMOUNT", "data": {}}
            if not name:
                return {"reply": _reply(lang, "need_name") or "Kiske naam pe likhna hai? Customer ka naam boliye.",
                        "action": "NEED_NAME", "data": {}}
            cust = T.find_or_create_customer(conn, name, shopkeeper_id=sid)
            T.add_entry(conn, cust["id"], "UDHAAR", amount, nlu.items_from(text), raw, shopkeeper_id=sid)
            bal = T.customer_balance(conn, cust["id"])
            reply = _reply(lang, "add", name=cust["name"], amt=T.fmt_money(amount), bal=T.fmt_money(bal))
            return {"reply": reply or f"{cust['name']} par {T.fmt_money(amount)} ka udhaar likh diya. "
                                      f"Total bakipada {T.fmt_money(bal)}.",
                    "action": "ENTRY_ADDED",
                    "data": {"customer": cust["name"], "amount": amount, "kind": "UDHAAR", "balance": bal}}

        if intent == "QUERY_BALANCE":
            if not name:
                return _totals_reply(conn, lang, sid)   # "kitna baki hai?" -> poori dukaan ka
            cust = T.find_customer(conn, name, sid)
            if not cust:
                return {"reply": _reply(lang, "not_found", name=name) or f"{name} khata me nahi hai.",
                        "action": "NOT_FOUND", "data": {}}
            bal = T.customer_balance(conn, cust["id"])
            reply = _reply(lang, "balance", name=cust["name"], amt=T.fmt_money(bal))
            return {"reply": reply or f"{cust['name']} ka total bakipada {T.fmt_money(bal)} hai.",
                    "action": "BALANCE", "data": {"customer": cust["name"], "balance": bal}}

        if intent == "SETTLE":
            if not name:
                return {"reply": "Kiska hisaab clear karna hai? Naam boliye.", "action": "NEED_NAME", "data": {}}
            cust = T.find_customer(conn, name, sid)
            if not cust:
                return {"reply": _reply(lang, "not_found", name=name) or f"{name} khata me nahi hai.",
                        "action": "NOT_FOUND", "data": {}}
            bal = T.customer_balance(conn, cust["id"])
            if bal <= 0:
                return {"reply": f"{cust['name']} ka hisaab pehle se clear hai — kuch baki nahi.",
                        "action": "BALANCE", "data": {"customer": cust["name"], "balance": bal}}
            _PENDING_SETTLE[sid] = (cust["id"], time.time())
            return {"reply": f"{cust['name']} ka {T.fmt_money(bal)} baki hai. Poora clear kar doon? "
                             "'Haan' ya 'nahi' boliye.",
                    "action": "CONFIRM_SETTLE",
                    "data": {"customer": cust["name"], "customer_id": cust["id"], "balance": bal}}

        if intent == "UNDO":
            return _undo_last(conn, sid)
        if intent == "LEND":
            if not name:
                return {"reply": "Kisko udhaar dena hai? Naam boliye.", "action": "NEED_NAME", "data": {}}
            return _lend_advice(conn, name, amount, sid)

        if intent == "BRIEFING":
            return run_tool("briefing", {}, sid=sid)
        if intent == "TOTALS":
            return _totals_reply(conn, lang, sid)
        if intent == "LIST_DUES":
            return run_tool("list_dues", {}, sid=sid)
        if intent == "SCORE":
            if not name:
                return {"reply": _reply(lang, "need_name") or "Kiska score dekhna hai? Naam boliye.",
                        "action": "NEED_NAME", "data": {}}
            return run_tool("trust_score", {"customer_name": name}, sid=sid)

    return {
        "reply": _reply(lang, "unknown") or
                 ("Ye main samajh nahi paaya. Bol dijiye jaise: "
                  "'Sharma ji ko do hazaar ka udhaar', 'kitna baki hai', ya 'aaj ka hisaab'."),
        "action": "UNKNOWN",
        "data": {"heard": text},
    }


# ---------------- LLM path (cloud mode brain) ----------------

async def evon_reply(text: str, sid: int = 1) -> dict | None:
    try:
        msgs = [{"role": "user", "content": text}]
        resp = await evon.chat(msgs, tools=TOOL_SCHEMA)
        msg = resp["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"reply": msg.get("content", "Ek baar phir boliye."), "action": "CHAT", "data": {}}
        call = calls[0]
        fn = call["function"]["name"]
        args = json.loads(call["function"].get("arguments") or "{}")
        result = run_tool(fn, args, transcript=text, sid=sid)
        # give the LLM a chance to phrase the result naturally
        try:
            follow = await evon.chat([
                {"role": "user", "content": text},
                msg,
                # tool_call_id is required by OpenAI-compatible APIs; without it
                # the follow-up call 400s and the reply stays unphrased.
                {"role": "tool", "tool_call_id": call.get("id", ""),
                 "name": fn, "content": json.dumps(result, ensure_ascii=False)},
            ])
            phrased = follow["choices"][0]["message"].get("content", "").strip()
            if phrased:
                result = {**result, "reply": phrased}
        except Exception:
            pass
        return result
    except ProviderNotConfigured:
        return None
    except Exception as e:  # never kill the voice loop on LLM hiccup
        log.warning("LLM path failed (%s) — falling back to rules", e)
        return None


# Money-destroying or advice intents never go to the LLM: the rule engine owns
# the confirmation step, the undo and the lend verdict, so a hallucinated tool
# call can't wipe a balance or invent a recommendation.
_RULES_ONLY = {"SETTLE", "UNDO", "LEND"}


async def handle_utterance(text: str, lang: str = "hi-IN", sid: int = 1) -> dict:
    """Main entry: the rule engine owns risky intents, the LLM handles the rest."""
    if evon_settings_ready():
        intent = nlu.classify(nlu.transliterate(text), lang)
        if intent not in _RULES_ONLY and sid not in _PENDING_SETTLE:
            result = await evon_reply(text, sid)
            if result:
                return {**result, "brain": "llm"}
    return {**rule_reply(text, lang, sid), "brain": "rules"}


def evon_settings_ready() -> bool:
    return bool(evon.settings.evon_api_url or evon.settings.evon_hf_model)
