"""Subah ki briefing — the 'AI manager' morning report."""
from datetime import date

from app.agent import tools as T
from app.analytics import trust_score


def build_briefing(conn, sid: int = 1) -> dict:
    tot = T.totals(conn, sid)
    dues = [c for c in T.customers_with_dues(conn, sid) if c["balance"] > 0]

    # promises made recently
    from datetime import datetime, timedelta
    today = date.today()
    due_soon = conn.execute(
        """SELECT p.*, c.name FROM promise p JOIN customer c ON c.id = p.customer_id
           WHERE p.status = 'PENDING' ORDER BY p.due_date ASC LIMIT 5"""
    ).fetchall()
    broken_recent = conn.execute(
        """SELECT p.*, c.name FROM promise p JOIN customer c ON c.id = p.customer_id
           WHERE p.status = 'BROKEN' ORDER BY p.id DESC LIMIT 3"""
    ).fetchall()

    lines = [f"Namaste! Aaj ke kaam — total udhaar {T.fmt_money(tot['udhaar_total'])} par hai, "
             f"aaj cash aaya {T.fmt_money(tot['cash_in_today'])}."]

    if due_soon:
        p = due_soon[0]
        lines.append(f"Sabse pehle: {p['name']} — {T.fmt_money(p['amount'])} ka wada "
                     f"{p['due_date']} ka hai.")
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
