"""Ledger operations — every agent action on the khata goes through these.

Kept as plain functions on sqlite so both the LLM tool-calling path and the
rule-engine path share exactly the same effects.
"""
import re
from datetime import date, datetime, timedelta

from app.db import db

HONORIFICS = {"ji", "bhai", "bhaiya", "seth", "sahab", "mr", "mrs", "uncle"}


def get_shopkeeper(conn, shopkeeper_id: int = 1):
    return conn.execute(
        "SELECT * FROM shopkeeper WHERE id = ?", (shopkeeper_id,)
    ).fetchone()


def find_customer(conn, name: str, shopkeeper_id: int = 1):
    """'Sharma ji' spoken -> matches 'Rajesh Sharma' in the ledger.

    People say surnames + honorifics, the khata stores full names — so match on
    any significant token, with doubled vowels collapsed (native-script transcripts
    transliterate to 'raajesh'/'sharmaa'-style spellings)."""
    from app.agent.nlu import fuzz

    q = name.strip().lower()
    if not q:
        return None
    rows = conn.execute(
        "SELECT * FROM customer WHERE shopkeeper_id = ? ORDER BY id", (shopkeeper_id,)
    ).fetchall()

    # best first: full spoken string inside a stored name
    for r in rows:
        if q in r["name"].lower():
            return r

    tokens = [fuzz(t) for t in re.split(r"[\s.]+", q) if t and t not in HONORIFICS]
    if not tokens:
        tokens = [fuzz(q)]
    for tok in sorted(set(tokens), key=len, reverse=True):
        if len(tok) < 3:
            continue
        for r in rows:
            if tok in fuzz(r["name"]):
                return r
    return None


def create_customer(conn, name: str, shopkeeper_id: int = 1, persona: str = ""):
    cur = conn.execute(
        "INSERT INTO customer (shopkeeper_id, name, persona) VALUES (?, ?, ?)",
        (shopkeeper_id, name.strip().title(), persona),
    )
    return conn.execute("SELECT * FROM customer WHERE id = ?", (cur.lastrowid,)).fetchone()


def find_or_create_customer(conn, name: str, shopkeeper_id: int = 1):
    if not name or not name.strip():
        return None
    row = find_customer(conn, name, shopkeeper_id)
    return row or create_customer(conn, name, shopkeeper_id)


def add_entry(conn, customer_id: int, kind: str, amount: float,
              items_text: str = "", raw_transcript: str = "", shopkeeper_id: int = 1):
    assert kind in ("UDHAAR", "PAYMENT")
    cur = conn.execute(
        """INSERT INTO entry (shopkeeper_id, customer_id, type, amount, items_text, raw_transcript)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (shopkeeper_id, customer_id, kind, amount, items_text, raw_transcript),
    )
    return cur.lastrowid


def customer_balance(conn, customer_id: int) -> float:
    row = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN type='UDHAAR' THEN amount END), 0) AS u,
             COALESCE(SUM(CASE WHEN type='PAYMENT' THEN amount END), 0) AS p
           FROM entry WHERE customer_id = ?""",
        (customer_id,),
    ).fetchone()
    return round(float(row["u"]) - float(row["p"]), 2)


def customers_with_dues(conn, shopkeeper_id: int = 1):
    rows = conn.execute(
        """SELECT c.id, c.name, c.persona, c.voice_id,
                  COALESCE(SUM(CASE WHEN e.type='UDHAAR' THEN e.amount END), 0) AS udhaar,
                  COALESCE(SUM(CASE WHEN e.type='PAYMENT' THEN e.amount END), 0) AS payment
           FROM customer c LEFT JOIN entry e ON e.customer_id = c.id
           WHERE c.shopkeeper_id = ?
           GROUP BY c.id""",
        (shopkeeper_id,),
    ).fetchall()
    out = []
    for r in rows:
        bal = round(float(r["udhaar"]) - float(r["payment"]), 2)
        out.append({"id": r["id"], "name": r["name"], "balance": bal,
                    "persona": r["persona"], "voice_id": r["voice_id"]})
    return out


def pending_promises(conn, customer_id: int):
    return conn.execute(
        """SELECT * FROM promise WHERE customer_id = ? AND status = 'PENDING'
           ORDER BY due_date ASC""",
        (customer_id,),
    ).fetchall()


def log_promise(conn, customer_id: int, amount: float, due_date: str, call_id: int | None = None):
    cur = conn.execute(
        "INSERT INTO promise (customer_id, amount, due_date, promised_on_call_id) VALUES (?, ?, ?, ?)",
        (customer_id, amount, due_date, call_id),
    )
    return cur.lastrowid


def settle_due_promises(conn, customer_id: int, pay_amount: float):
    """A payment auto-settles the oldest pending promises it covers."""
    remaining = pay_amount
    for p in pending_promises(conn, customer_id):
        if remaining <= 0:
            break
        remaining -= float(p["amount"])
        conn.execute("UPDATE promise SET status = 'KEPT' WHERE id = ?", (p["id"],))


def totals(conn, shopkeeper_id: int = 1):
    today = date.today().isoformat()
    row = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN type='UDHAAR' THEN amount END), 0) AS udhaar_total,
             COALESCE(SUM(CASE WHEN type='PAYMENT' THEN amount END), 0) AS cash_in_total,
             COALESCE(SUM(CASE WHEN type='UDHAAR' AND date(created_at)=? THEN amount END), 0) AS udhaar_today,
             COALESCE(SUM(CASE WHEN type='PAYMENT' AND date(created_at)=? THEN amount END), 0) AS cash_in_today
           FROM entry WHERE shopkeeper_id = ?""",
        (today, today, shopkeeper_id),
    ).fetchone()
    return {k: round(float(row[k]), 2) for k in row.keys()}


def recent_entries(conn, limit: int = 30, shopkeeper_id: int = 1):
    return conn.execute(
        """SELECT e.*, c.name AS customer_name FROM entry e
           JOIN customer c ON c.id = e.customer_id
           WHERE e.shopkeeper_id = ? ORDER BY e.id DESC LIMIT ?""",
        (shopkeeper_id, limit),
    ).fetchall()


def parse_due_date(text: str) -> str:
    """Hinglish relative dates -> ISO date. 'kal', 'parso', 'aaj', '15 tareekh',
    'agle somvar' etc."""
    t = text.lower()
    weekdays = {
        "somvar": 0, "mangalvar": 1, "budhvar": 2, "guruvar": 3, "bruhaspativar": 3,
        "shukravar": 4, "shanivar": 5, "ravitvar": 6, "sunday": 6, "monday": 0,
        "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5,
    }
    today = date.today()
    if "parso" in t or "parson" in t:
        return (today + timedelta(days=2)).isoformat()
    if "kal" in t:
        return (today + timedelta(days=1)).isoformat()
    if "aaj" in t:
        return today.isoformat()
    if "agle hafte" in t or "next week" in t:
        return (today + timedelta(days=7)).isoformat()
    for name, wd in weekdays.items():
        if name in t:
            delta = (wd - today.weekday()) % 7 or 7
            return (today + timedelta(days=delta)).isoformat()
    # "15 tareekh" / "15 tarikh" / bare "15 ko"
    for token in t.replace(",", " ").split():
        tok = token.strip(".,")
        if tok.isdigit() and 1 <= int(tok) <= 31:
            try:
                d = today.replace(day=int(tok))
                if d < today:
                    d = d.replace(month=today.month % 12 + 1) if today.month < 12 else today.replace(year=today.year + 1, month=1)
            except ValueError:
                continue
            return d.isoformat()
    return (today + timedelta(days=1)).isoformat()


def fmt_money(x: float) -> str:
    if x == int(x):
        return f"₹{int(x):,}"
    return f"₹{x:,.2f}"
