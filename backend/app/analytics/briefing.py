"""Subah ki briefing — the 'AI manager' morning report."""
from datetime import date

from app.agent import tools as T
from app.analytics import trust_score


_MONTHS_HI = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]


def _when(iso: str) -> str:
    """ISO date -> something a voice can say: aaj / kal / parso / 18 November."""
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    delta = (d - date.today()).days
    if delta in (0, 1, 2):
        return ("aaj", "kal", "parso")[delta]
    return f"{d.day} {_MONTHS_HI[d.month - 1]}"


def build_briefing(conn, sid: int = 1) -> dict:
    T.expire_promises(conn, sid)          # overdue wade -> BROKEN before reporting
    tot = T.totals(conn, sid)
    dues = [c for c in T.customers_with_dues(conn, sid) if c["balance"] > 0]

    # promises made recently
    from datetime import datetime, timedelta
    today = date.today()
    due_soon = conn.execute(
        """SELECT p.*, c.name FROM promise p JOIN customer c ON c.id = p.customer_id
           WHERE p.status = 'PENDING' AND c.shopkeeper_id = ?
           ORDER BY p.due_date ASC LIMIT 5""", (sid,)
    ).fetchall()
    broken_recent = conn.execute(
        """SELECT p.*, c.name FROM promise p JOIN customer c ON c.id = p.customer_id
           WHERE p.status = 'BROKEN' AND c.shopkeeper_id = ?
           ORDER BY p.due_date DESC, p.id DESC LIMIT 3""", (sid,)
    ).fetchall()

    if not dues and not tot["udhaar_total"]:
        text = ("Namaste! Khata abhi khaali hai. Mic dabake boliye — jaise "
                "'Sharma ji ko paanch sau ka udhaar lagana' — aur pehli entry likh jayegi.")
        return {"reply": text, "action": "BRIEFING",
                "data": {"totals": tot, "dues": [], "promises_due": [], "risky": []}}

    lines = [f"Namaste! Aaj ke kaam — kul baki udhaar {T.fmt_money(tot['outstanding'])} par hai, "
             f"aaj cash aaya {T.fmt_money(tot['cash_in_today'])}."]

    if due_soon:
        p = due_soon[0]
        lines.append(f"Sabse pehle: {p['name']} — {T.fmt_money(p['amount'])} ka wada "
                     f"{_when(p['due_date'])} ka hai.")
    if broken_recent:
        lines.append(f"Dhyan dijiye: {broken_recent[0]['name']} ne pichhla wada toda tha — "
                     "isse pehle purana clear karwa lein.")
    if dues:
        top = sorted(dues, key=lambda c: c["balance"], reverse=True)[0]
        lines.append(f"Sabse bada baki {top['name']} ka hai — {T.fmt_money(top['balance'])}. "
                     f"Aaj {min(3, len(dues))} customers ko call karne hain.")

    risky = [s for s in trust_score.all_scores(conn, sid) if s["score"] < 40]
    if risky:
        lines.append(f"Aur {risky[0]['customer']} ka score {risky[0]['score']} hai — udhaar sambhal ke.")

    text = " ".join(lines)
    return {"reply": text, "action": "BRIEFING",
            "data": {"totals": tot, "dues": dues,
                     "promises_due": [dict(r) for r in due_soon],
                     "risky": [r["customer"] for r in risky]}}
