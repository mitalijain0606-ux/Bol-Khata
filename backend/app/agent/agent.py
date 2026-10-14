"""The agent brain: Evon tool-calling when configured, Hinglish rule engine otherwise.

Both paths produce the same shape:
  {"reply": str, "action": str, "data": {...}}  — frontend speaks `reply`.
"""
import json
import logging

from app.agent import nlu, tools as T
from app.analytics import trust_score
from app.db import db
from app.gnani import evon
from app.gnani.stt import ProviderNotConfigured

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


def run_tool(name: str, args: dict, transcript: str = "") -> dict:
    with db() as conn:
        if name == "add_entry":
            cust = T.find_or_create_customer(conn, args.get("customer_name", ""))
            if not cust or not args.get("amount"):
                return {"error": "customer ya amount missing"}
            T.add_entry(conn, cust["id"], args.get("kind", "UDHAAR"),
                        float(args["amount"]), args.get("items_text", ""), transcript)
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
            cust = T.find_customer(conn, args.get("customer_name", ""))
            if not cust:
                return {"reply": "Ye customer khata me nahi mila. Naam phir se boliye.", "action": "NOT_FOUND", "data": {}}
            bal = T.customer_balance(conn, cust["id"])
            return {"reply": f"{cust['name']} ka total bakipada {T.fmt_money(bal)} hai.",
                    "action": "BALANCE", "data": {"customer": cust["name"], "balance": bal}}
        if name == "totals_today":
            tot = T.totals(conn)
            return {"reply": f"Aaj ka udhaar {T.fmt_money(tot['udhaar_today'])} bana, "
                             f"cash aaya {T.fmt_money(tot['cash_in_today'])}. "
                             f"Kul udhaar abhi {T.fmt_money(tot['udhaar_total'])} par hai.",
                    "action": "TOTALS", "data": tot}
        if name == "list_dues":
            dues = [c for c in T.customers_with_dues(conn) if c["balance"] > 0]
            if not dues:
                return {"reply": "Aaj sab ka hisaab clear hai — kisi ka udhaar nahi!", "action": "LIST_DUES", "data": []}
            names = ", ".join(f"{c['name']} {T.fmt_money(c['balance'])}" for c in dues[:8])
            return {"reply": f"Ye logon ka udhaar baki hai: {names}.", "action": "LIST_DUES", "data": dues}
        if name == "briefing":
            from app.analytics.briefing import build_briefing
            return build_briefing(conn)
        if name == "trust_score":
            cust = T.find_customer(conn, args.get("customer_name", ""))
            if not cust:
                return {"reply": "Ye customer khata me nahi mila.", "action": "NOT_FOUND", "data": {}}
            res = trust_score.compute(conn, cust["id"])
            return {"reply": f"{cust['name']} ka bharaut-score {res['score']}/100 hai. {res['one_liner']}",
                    "action": "TRUST_SCORE", "data": res}
    return {"reply": "Samajh nahi aaya, dobara boliye.", "action": "UNKNOWN", "data": {}}


# ---------------- rule-engine path (Mock Mode brain) ----------------

def rule_reply(text: str) -> dict:
    intent = nlu.classify(text)
    amount = nlu.parse_amount(text)
    with db() as conn:
        known = [r["name"] for r in conn.execute("SELECT name FROM customer").fetchall()]
        name = nlu.find_customer_name(text, known)

        if intent == "PAYMENT":
            if not amount:
                return {"reply": "Kitne ka payment aaya? Amount bol dijiye.", "action": "NEED_AMOUNT", "data": {}}
            cust = T.find_or_create_customer(conn, name) if name else None
            if not cust:
                return {"reply": "Kis customer ne diye? Naam bhi bol dijiye.", "action": "NEED_NAME", "data": {}}
            T.add_entry(conn, cust["id"], "PAYMENT", amount, nlu.items_from(text), text)
            T.settle_due_promises(conn, cust["id"], amount)
            bal = T.customer_balance(conn, cust["id"])
            return {"reply": f"Note ho gaya — {cust['name']} ka payment {T.fmt_money(amount)}. "
                             f"Bakipada ab {T.fmt_money(bal)}.",
                    "action": "ENTRY_ADDED",
                    "data": {"customer": cust["name"], "amount": amount, "kind": "PAYMENT", "balance": bal}}

        if intent == "ADD_UDHAAR":
            if not amount:
                return {"reply": "Kitne ka udhaar lagana hai? Amount boliye.", "action": "NEED_AMOUNT", "data": {}}
            if not name:
                return {"reply": "Kiske naam pe likhna hai? Customer ka naam boliye.", "action": "NEED_NAME", "data": {}}
            cust = T.find_or_create_customer(conn, name)
            T.add_entry(conn, cust["id"], "UDHAAR", amount, nlu.items_from(text), text)
            bal = T.customer_balance(conn, cust["id"])
            return {"reply": f"{cust['name']} par {T.fmt_money(amount)} ka udhaar likh diya. "
                             f"Total bakipada {T.fmt_money(bal)}.",
                    "action": "ENTRY_ADDED",
                    "data": {"customer": cust["name"], "amount": amount, "kind": "UDHAAR", "balance": bal}}

        if intent == "QUERY_BALANCE":
            if not name:
                return {"reply": "Kis ka baki dekhna hai? Naam boliye.", "action": "NEED_NAME", "data": {}}
            return run_tool("query_balance", {"customer_name": name})

        if intent == "SETTLE":
            if not name:
                return {"reply": "Kiska hisaab clear karna hai? Naam boliye.", "action": "NEED_NAME", "data": {}}
            cust = T.find_customer(conn, name)
            if not cust:
                return {"reply": f"{name} khata me nahi hai.", "action": "NOT_FOUND", "data": {}}
            bal = T.customer_balance(conn, cust["id"])
            if bal > 0:
                T.add_entry(conn, cust["id"], "PAYMENT", bal, "", text)
                T.settle_due_promises(conn, cust["id"], bal)
            return {"reply": f"{cust['name']} ka hisaab poora clear — {T.fmt_money(bal)} settle.",
                    "action": "SETTLED", "data": {"customer": cust["name"], "balance": 0.0}}

        if intent == "BRIEFING":
            return run_tool("briefing", {})
        if intent == "TOTALS":
            return run_tool("totals_today", {})
        if intent == "LIST_DUES":
            return run_tool("list_dues", {})
        if intent == "SCORE" and name:
            return run_tool("trust_score", {"customer_name": name})

    return {
        "reply": "Ye main samajh nahi paaya. Bol dijiye jaise: "
                 "'Sharma ji ko do hazaar ka udhaar', 'kitna baki hai', ya 'aaj ka hisaab'.",
        "action": "UNKNOWN",
        "data": {"heard": text},
    }


# ---------------- Evon path (Gnani Mode brain) ----------------

async def evon_reply(text: str) -> dict | None:
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
        result = run_tool(fn, args, transcript=text)
        # give Evon a chance to phrase the result naturally
        try:
            follow = await evon.chat([
                {"role": "user", "content": text},
                msg,
                {"role": "tool", "content": json.dumps(result, ensure_ascii=False)},
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
        log.warning("Evon path failed (%s) — falling back to rules", e)
        return None


async def handle_utterance(text: str) -> dict:
    """Main entry: brain decides who answers."""
    if evon_settings_ready():
        result = await evon_reply(text)
        if result:
            return {**result, "brain": "evon"}
    return {**rule_reply(text), "brain": "rules"}


def evon_settings_ready() -> bool:
    return bool(evon.settings.evon_api_url or evon.settings.evon_hf_model)
