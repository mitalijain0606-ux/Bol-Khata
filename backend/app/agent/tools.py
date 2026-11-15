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
    if kind not in ("UDHAAR", "PAYMENT"):
        raise ValueError("entry type must be UDHAAR or PAYMENT")
    if not amount or amount <= 0:
        raise ValueError("amount must be positive")
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


def settle_due_promises(conn, customer_id: int, pay_amount: float = 0.0):
    """Mark pending promises KEPT once the money paid since the promise was made
    covers them (oldest first). A ₹100 payment no longer 'keeps' a ₹2,000 promise,
    and two part-payments that add up to the promise do."""
    pending = conn.execute(
        "SELECT * FROM promise WHERE customer_id = ? AND status = 'PENDING' ORDER BY id ASC",
        (customer_id,),
    ).fetchall()
    if not pending:
        return
    since = min(p["created_at"] or "" for p in pending)
    paid = float(conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM entry "
        "WHERE customer_id = ? AND type = 'PAYMENT' AND created_at > ?",
        (customer_id, since),
    ).fetchone()["s"])
    # money already counted towards promises kept in the same window
    paid -= float(conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM promise "
        "WHERE customer_id = ? AND status = 'KEPT' AND created_at >= ?",
        (customer_id, since),
    ).fetchone()["s"])
    cleared = customer_balance(conn, customer_id) <= 0
    for p in pending:
        if cleared or paid + 0.005 >= float(p["amount"]):
            conn.execute("UPDATE promise SET status = 'KEPT' WHERE id = ?", (p["id"],))
            paid -= float(p["amount"])
        else:
            break


def expire_promises(conn, shopkeeper_id: int | None = None) -> int:
    """PENDING -> BROKEN once the due date has passed without the money arriving."""
    today = date.today().isoformat()
    sql = ("UPDATE promise SET status = 'BROKEN' WHERE status = 'PENDING' AND due_date < ?")
    args: tuple = (today,)
    if shopkeeper_id is not None:
        sql += " AND customer_id IN (SELECT id FROM customer WHERE shopkeeper_id = ?)"
        args = (today, shopkeeper_id)
    return conn.execute(sql, args).rowcount


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
    out = {k: round(float(row[k]), 2) for k in row.keys()}
    # what is actually still owed (lifetime udhaar minus everything paid back)
    out["outstanding"] = round(out["udhaar_total"] - out["cash_in_total"], 2)
    return out


def recent_entries(conn, limit: int = 30, shopkeeper_id: int = 1):
    return conn.execute(
        """SELECT e.*, c.name AS customer_name FROM entry e
           JOIN customer c ON c.id = e.customer_id
           WHERE e.shopkeeper_id = ? ORDER BY e.id DESC LIMIT ?""",
        (shopkeeper_id, limit),
    ).fetchall()


_WEEKDAYS = {
    "somvar": 0, "somwar": 0, "mangalvar": 1, "mangalwar": 1, "budhvar": 2, "budhwar": 2,
    "guruvar": 3, "guruwar": 3, "bruhaspativar": 3, "shukravar": 4, "shukrawar": 4,
    "shanivar": 5, "shaniwar": 5, "ravivar": 6, "raviwar": 6, "ravitvar": 6, "itwar": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
    "saturday": 5, "sunday": 6,
}
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _next_day_of_month(day: int, today: date) -> date | None:
    """Next calendar date whose day-of-month is `day` (today counts)."""
    y, m = today.year, today.month
    for _ in range(13):
        try:
            d = date(y, m, day)
            if d >= today:
                return d
        except ValueError:
            pass                       # e.g. the 31st in a 30-day month
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return None


def parse_due_date(text: str) -> str:
    """Hinglish relative dates -> ISO date. 'kal', 'parso', 'aaj', '15 tareekh',
    '19 November', 'agle somvar' etc. Whole-word matching, so 'aajkal' or
    'bilkul' are not read as a date. Default: tomorrow."""
    t = text.lower()
    today = date.today()
    words = set(re.findall(r"[a-z]+", t))
    if words & {"parso", "parson", "parsu"}:
        return (today + timedelta(days=2)).isoformat()
    if "kal" in words:
        return (today + timedelta(days=1)).isoformat()
    if "agle hafte" in t or "next week" in t or "ek hafte" in t:
        return (today + timedelta(days=7)).isoformat()
    for name, wd in _WEEKDAYS.items():
        if name in words:
            delta = (wd - today.weekday()) % 7 or 7
            return (today + timedelta(days=delta)).isoformat()
    # "19 November" / "15 tareekh" / "15 ko"
    m = re.search(r"\b(\d{1,2})\s*([a-z]+)", t)
    if m and 1 <= int(m.group(1)) <= 31:
        day, word = int(m.group(1)), m.group(2)
        if word[:3] in _MONTHS and len(word) >= 3 and word not in ("mahine",):
            for y in (today.year, today.year + 1):
                try:
                    d = date(y, _MONTHS[word[:3]], day)
                except ValueError:
                    continue
                if d >= today:
                    return d.isoformat()
        elif word in ("tareekh", "tarikh", "tarik", "ko", "tak"):
            d = _next_day_of_month(day, today)
            if d:
                return d.isoformat()
    if words & {"aaj", "aj", "abhi"}:
        return today.isoformat()
    return (today + timedelta(days=1)).isoformat()


def fmt_money(x: float) -> str:
    if x == int(x):
        return f"₹{int(x):,}"
    return f"₹{x:,.2f}"
