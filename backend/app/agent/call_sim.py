"""Collections call simulator — Bol-Khata's outbound agent vs synthetic debtors.

Three fake-debtor personas (promiser / avoider / bargainer) driven by a state
machine. In Gnani Mode the AGENT's lines can be upgraded to Evon, but the
template brain below already produces a fully working, free, repeatable demo —
no real phone numbers, no real calls (DPDP-safe).

Server drives the whole exchange:
  start()  -> agent opening line + debtor's first reaction
  step()   -> next (agent_line, debtor_line, state) exchange
  say()    -> shopkeeper barge-in: debtor reacts to an arbitrary line
  end()    -> persist call, summary, sentiment, promise
"""
import random
import json
from datetime import date, datetime, timedelta

from app.agent import nlu, tools as T
from app.db import db

PERSONAS = {
    "promiser": {
        "label": "Pakka-wala",
        "excuse": "Haan bhaiya, samajh gaya. Bas is hafte thoda tang tha.",
        "promise_line": "Aap chinta mat karo, {date_word} tak poora {amount} de dunga, pakka.",
        "agree_fast": True,
    },
    "avoider": {
        "label": "Talne-wala",
        "excuse": "Arre bhaiya, dukaan ki haalat dekh lo... paise hi nahi aaye abhi.",
        "promise_line": "Theek hai theek hai... {date_word} karne ki koshish karunga.",
        "agree_fast": False,
    },
    "bargainer": {
        "label": "Bhav-taai-wala",
        "excuse": "Bhaiya itna to maaf kar do, {partial} to de hi deta hoon aaj. Baaki baad me.",
        "promise_line": "Aaj {partial} de deta hoon, baaki {rest} {date_word} tak pakka.",
        "agree_fast": False,
    },
}

DATE_WORDS = {
    (date.today() + timedelta(days=1)).isoformat(): "kal",
    (date.today() + timedelta(days=2)).isoformat(): "parso",
    date.today().isoformat(): "aaj",
}


def _date_word(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso).date()
    except ValueError:
        return iso
    if d == date.today():
        return "aaj"
    if d == date.today() + timedelta(days=1):
        return "kal"
    if d == date.today() + timedelta(days=2):
        return "parso"
    return d.strftime("%d %B")


class CallSim:
    """In-memory conversation state; persisted to call_record on end()."""

    def __init__(self, call_id: int, customer: dict, balance: float,
                  broken_count: int, persona_key: str, shop_name: str):
        self.call_id = call_id
        self.customer = customer
        self.balance = balance
        self.broken_count = broken_count
        self.persona_key = persona_key
        self.persona = PERSONAS[persona_key]
        self.shop_name = shop_name
        self.turn = 0
        self.max_turns = 6
        self.transcript: list[dict] = []
        self.state = "OPEN"          # OPEN -> EXCUSED -> NEGOTIATE -> SETTLED_PROMISE / REFUSED / PARTIAL
        self.promise: dict | None = None
        self.partial_today: float | None = None
        self.agent_opening = self._agent_opening()
        debtor_first = (
            f"Haan bhaiya, boliye." if persona_key == "promiser"
            else "Haan haan, bol raha hoon bhaiya..."
        )
        self.transcript.append({"who": "agent", "text": self.agent_opening})
        self.transcript.append({"who": "customer", "text": debtor_first})
        self.last_debtor = debtor_first

    # ---------- agent lines ----------

    def _agent_opening(self) -> str:
        amt = T.fmt_money(self.balance)
        base = (f"Namaste {self.customer['name']} ji, main {self.shop_name} ki taraf se "
                f"bol raha hoon. Khata ke hisaab se {amt} udhaar baaki hai — "
                f"kab tak de paayenge?")
        if self.broken_count:
            base = (f"Namaste {self.customer['name']} ji, {self.shop_name} se baat kar raha hoon. "
                    f"Pichhli baar aapne wada kiya tha par ho nahi paaya — "
                    f"abhi {amt} baki hai. Is baar pakka date bata dijiye.")
        return base

    def _agent_line(self, debtor_text: str) -> str:
        amt = T.fmt_money(self.balance)
        if self.state == "OPEN":
            if self.persona["agree_fast"]:
                self.state = "SETTLED_PROMISE"
                d = T.parse_due_date(debtor_text)
                self.promise = {"amount": self.balance, "due_date": d}
                return (f"Bahut badhiya! To main note kar leta hoon — {T.fmt_money(self.balance)} "
                        f"{_date_word(d)} tak. Aapka bharaut-score bhi isse sudhar jayega. Dhanyavaad!")
            self.state = "EXCUSED"
            return (f"Samajh sakte hain ji, lekin {amt} kaafi dino se pending hai. "
                    f"Mujhe sirf ek pakka date chahiye — kab de paayenge?")
        if self.state == "EXCUSED":
            self.state = "NEGOTIATE"
            if self.broken_count:
                return (f"Dekhiye, pichhle wada bhi adhoora raha. Naya wada todiye — "
                        f"aaj se ek hafte ke andar {amt} ho jayega?")
            return (f"Thik hai ji, mushkil waqt hai. To kya {amt} agle hafte ke andar "
                    f"ho jayega? Date pakki kar lete hain.")
        if self.state == "NEGOTIATE":
            d = T.parse_due_date(debtor_text)
            partial = nlu.parse_amount(debtor_text)
            # partial payment hi maano agar amount balance ka meaningful hissa ho
            # (warna '19 October' jaisi date ke digit amount ban jaate hain)
            if partial and partial >= self.balance * 0.1 and partial < self.balance:
                self.partial_today = partial
                rest = round(self.balance - partial, 2)
                self.promise = {"amount": rest, "due_date": d}
                self.state = "PARTIAL"
                return (f"Theek hai — aaj {T.fmt_money(partial)} aur baki {T.fmt_money(rest)} "
                        f"{_date_word(d)} tak. Main dono note kar raha hoon. Shukriya ji!")
            self.state = "SETTLED_PROMISE"
            self.promise = {"amount": self.balance, "due_date": d}
            return (f"Pakka {_date_word(d)} tak? Main note kar raha hoon — "
                    f"{T.fmt_money(self.balance)}, {_date_word(d)}. Wada record ho gaya, dhanyavaad!")
        return f"Theek hai ji, note kar liya. Shukriya!"

    def _agent_close(self, refused: bool) -> str:
        if refused:
            self.state = "REFUSED"
            return ("Koi baat nahi ji, jab ho jaye bata dijiye. "
                    "Par yaad rakhiye, bharaut-score gir raha hai — jaldi settle karwa lein. Dhanyavaad.")
        return "Shukriya ji, aapka din shubh ho!"

    # ---------- debtor reactions ----------

    def _debtor_reply(self, agent_text: str) -> str:
        amt = T.fmt_money(self.balance)
        if self.state == "OPEN":
            return self.persona["excuse"].format(partial=T.fmt_money(self.balance * 0.4))
        if self.state == "EXCUSED":
            if self.persona_key == "avoider":
                return random.choice([
                    "Dekhiye na bhaiya, mandi hi kharab hai... parso de deta hoon.",
                    "Bhaiya thoda sabar... agle somvar tak karne ki koshish.",
                ])
            return random.choice([
                f"Bhaiya aap boliye, {amt} kahan se aa jaye achanak...",
                "Sach kahun to is mahine ghar ka kharcha hi bhaari tha.",
            ])
        if self.state == "NEGOTIATE":
            if self.persona_key == "bargainer":
                partial = round(self.balance * random.uniform(0.25, 0.45), -1)
                return self.persona["promise_line"].format(
                    partial=T.fmt_money(partial), rest=T.fmt_money(self.balance - partial),
                    date_word="kal")
            d = T.parse_due_date(random.choice(["kal", "parso", "agle somvar"]))
            return self.persona["promise_line"].format(amount=amt, date_word=_date_word(d))
        if self.state == "PARTIAL":
            return "Haan bhaiya, aap ka bharosa rakhiye, baki bhi ho jayega."
        if self.state == "REFUSED":
            return random.choice([
                "Bhaiya himmat mat haariye, main koshish karunga...",
                "Thoda waqt de dijiye, sab theek kar dunga.",
            ])
        return "Ji bilkul, note kar lijiye."

    # ---------- public API ----------

    def step(self) -> dict:
        finished = self.state in ("SETTLED_PROMISE", "PARTIAL", "REFUSED") or self.turn >= self.max_turns
        if finished:
            refused = self.state not in ("SETTLED_PROMISE", "PARTIAL")
            close_line = self._agent_close(refused=refused)
            debtor_line = self._debtor_reply(agent_text=close_line)
            self.transcript.append({"who": "agent", "text": close_line})
            self.transcript.append({"who": "customer", "text": debtor_line})
            return {"done": True, "agent": close_line, "customer": debtor_line,
                    "state": self.state, "promise": self.promise,
                    "partial_today": self.partial_today}
        self.turn += 1
        agent_line = self._agent_line(self.last_debtor)
        debtor_line = self._debtor_reply(agent_text=agent_line)
        self.transcript.append({"who": "agent", "text": agent_line})
        self.transcript.append({"who": "customer", "text": debtor_line})
        self.last_debtor = debtor_line
        return {"done": self.state in ("SETTLED_PROMISE", "PARTIAL"),
                "agent": agent_line, "customer": debtor_line,
                "state": self.state, "promise": self.promise,
                "partial_today": self.partial_today}

    def say(self, text: str) -> dict:
        """Shopkeeper barge-in: debtor reacts to an arbitrary line."""
        self.transcript.append({"who": "agent", "text": f"(malik) {text}"})
        t = text.lower()
        if any(w in t for w in ("kitna", "kab", "baki", "due", "udhaar")):
            reply = "Arre bas kal-parso me adjust kar dunga bhaiya, pakka."
            self.state = "NEGOTIATE"
        elif any(w in t for w in ("shukriya", "theek", "dhanyavaad", "chalo")):
            reply = "Ji bilkul bhaiya, dhanyavaad aapka!"
        else:
            reply = random.choice([
                "Ji ji, samajh gaya bhaiya.",
                "Haan, aap sahi keh rahe hain.",
            ])
        self.transcript.append({"who": "customer", "text": reply})
        self.last_debtor = reply
        return {"done": False, "customer": reply, "state": self.state}

    def end(self) -> dict:
        if self.promise:
            with db() as conn:
                T.log_promise(conn, self.customer["id"], self.promise["amount"],
                              self.promise["due_date"], call_id=self.call_id)
            if self.partial_today:
                with db() as conn:
                    T.add_entry(conn, self.customer["id"], "PAYMENT", self.partial_today,
                                "Call pe partial payment", "",
                                shopkeeper_id=self.customer["shopkeeper_id"])
        transcript_json = json.dumps(self.transcript, ensure_ascii=False)
        summary, sentiment, excuse = self._summarize()
        outcome = "PROMISE" if self.promise else ("PARTIAL" if self.partial_today else "REFUSED")
        with db() as conn:
            conn.execute(
                """UPDATE call_record SET transcript=?, summary=?, sentiment=?, excuse_type=?,
                       outcome=?, duration_sec=? WHERE id=?""",
                (transcript_json, summary, sentiment, excuse, outcome, self.turn * 25, self.call_id),
            )
        return {"summary": summary, "outcome": outcome, "sentiment": sentiment,
                "promise": self.promise, "partial_today": self.partial_today}

    def _summarize(self):
        full_text = " ".join(m["text"] for m in self.transcript).lower()
        positives = sum(w in full_text for w in ("pakka", "zaroor", "sorry", "shukriya", "theek"))
        negatives = sum(w in full_text for w in ("nahi", "mandi", "mushkil", "tang"))
        sentiment = "positive" if positives > negatives else ("negative" if negatives > positives else "neutral")
        excuse = self.persona["label"]
        if self.promise:
            pw = _date_word(self.promise["due_date"])
            summary = (f"Call pe {self.customer['name']} ne {T.fmt_money(self.promise['amount'])} "
                       f"ka wada {pw} tak kiya.")
            if self.partial_today:
                summary = (f"{T.fmt_money(self.partial_today)} aaj ka partial note hua; "
                           + summary)
        else:
            summary = f"{self.customer['name']} ne aaj wada nahi kiya — follow-up call chahiye."
        return summary, sentiment, excuse


def start_call(customer_id: int, shopkeeper_id: int = 1) -> dict:
    with db() as conn:
        cust = conn.execute("SELECT * FROM customer WHERE id = ?", (customer_id,)).fetchone()
        if not cust:
            return {"error": "customer not found"}
        balance = T.customer_balance(conn, customer_id)
        broken = conn.execute(
            "SELECT COUNT(*) AS c FROM promise WHERE customer_id=? AND status='BROKEN'",
            (customer_id,),
        ).fetchone()["c"]
        shop = T.get_shopkeeper(conn, shopkeeper_id)
        persona_key = cust["persona"] if cust["persona"] in PERSONAS else random.choice(list(PERSONAS))
        cur = conn.execute("INSERT INTO call_record (customer_id, outcome) VALUES (?, 'IN_PROGRESS')",
                           (customer_id,))
        call_id = cur.lastrowid

    sim = CallSim(call_id, dict(cust), balance, broken, persona_key,
                  shop["shop_name"] if shop else "dukaan")
    _CALLS[call_id] = sim
    return {
        "call_id": call_id,
        "customer": {"id": cust["id"], "name": cust["name"], "persona": persona_key,
                     "persona_label": PERSONAS[persona_key]["label"]},
        "balance": balance,
        "broken_count": broken,
        "agent": sim.agent_opening,
        "customer_line": sim.last_debtor,
    }


def step_call(call_id: int) -> dict:
    sim = _CALLS.get(call_id)
    if not sim:
        return {"error": "call not found (server restart?)"}
    return sim.step()


def say_to_call(call_id: int, text: str) -> dict:
    sim = _CALLS.get(call_id)
    if not sim:
        return {"error": "call not found (server restart?)"}
    return sim.say(text)


def end_call(call_id: int) -> dict:
    sim = _CALLS.pop(call_id, None)
    if not sim:
        return {"error": "call not found"}
    return sim.end()


_CALLS: dict[int, CallSim] = {}
