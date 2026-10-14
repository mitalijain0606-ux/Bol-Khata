"""Bharaut-Score — explainable trust score per customer.

score = 100 - 25*tode_wade - 10*late_payments - 5*purane_baki
Pure SQLite, no black box. Frontend shows the breakdown.
"""
from datetime import date, datetime


def compute(conn, customer_id: int) -> dict:
    cust = conn.execute("SELECT * FROM customer WHERE id = ?", (customer_id,)).fetchone()

    promises = conn.execute(
        "SELECT status, due_date, created_at FROM promise WHERE customer_id = ?",
        (customer_id,),
    ).fetchall()
    payments = conn.execute(
        "SELECT amount, created_at, status FROM entry WHERE customer_id = ? AND type = 'PAYMENT'",
        (customer_id,),
    ).fetchall()
    udhaar_rows = conn.execute(
        "SELECT amount, created_at FROM entry WHERE customer_id = ? AND type = 'UDHAAR'",
        (customer_id,),
    ).fetchall()

    # payments vs udhaars timeline -> late count
    udhaar_dates = [datetime.fromisoformat(r["created_at"]).date() for r in udhaar_rows if r["created_at"]]
    late_payments = 0
    for p in payments:
        d = datetime.fromisoformat(p["created_at"]).date() if p["created_at"] else None
        if d and udhaar_dates and (d - min(udhaar_dates)).days > 15:
            late_payments += 1

    broken = sum(1 for p in promises if p["status"] == "BROKEN")
    kept = sum(1 for p in promises if p["status"] == "KEPT")
    pending = [p for p in promises if p["status"] == "PENDING"]
    overdue_pending = 0
    today = date.today()
    for p in pending:
        try:
            if datetime.fromisoformat(p["due_date"]).date() < today:
                overdue_pending += 1
        except ValueError:
            pass

    bal_rows = conn.execute(
        """SELECT COALESCE(SUM(CASE WHEN type='UDHAAR' THEN amount END),0) AS u,
                  COALESCE(SUM(CASE WHEN type='PAYMENT' THEN amount END),0) AS p
           FROM entry WHERE customer_id = ?""",
        (customer_id,),
    ).fetchone()
    balance = float(bal_rows["u"]) - float(bal_rows["p"])

    stale_active = 1 if balance > 0 and udhaar_dates and (today - max(udhaar_dates)).days > 30 else 0

    score = 100 - 25 * broken - 10 * late_payments - 5 * stale_active
    score = max(0, min(100, score))

    parts = []
    if broken:
        parts.append(f"-{25 * broken} ({broken} wada toda)")
    if late_payments:
        parts.append(f"-{10 * late_payments} (der se payment)")
    if stale_active:
        parts.append("-5 (30+ din purana baki)")
    if kept:
        parts.append(f"+{min(20, kept * 5)} bonus ({kept} wade poore kiye)")
        score = min(100, score + min(20, kept * 5))

    if score >= 80:
        band, one = "Pakka", "Bharosa kar sakte hain — time pe deta hai."
    elif score >= 55:
        band, one = "Theek-thaak", "Dete hai par der se — chhota udhaar theek hai."
    elif score >= 35:
        band, one = "Sambhal ke", "Wade tode hain — bade udhaar se pehle purana clear karwayein."
    else:
        band, one = "Risky", "Ye customer ke paise aksar atakte hain — udhaar rok dijiye."
    if parts:
        one += f" ({', '.join(parts)})"

    return {
        "customer": cust["name"] if cust else str(customer_id),
        "score": score,
        "band": band,
        "one_liner": one,
        "breakdown": {
            "promises_kept": kept,
            "promises_broken": broken,
            "promises_pending": len(pending),
            "promises_overdue": overdue_pending,
            "late_payments": late_payments,
            "stale_balance": bool(stale_active),
            "adjustments": parts,
        },
        "balance": round(balance, 2),
    }


def all_scores(conn) -> list[dict]:
    out = []
    for row in conn.execute("SELECT id FROM customer ORDER BY id").fetchall():
        out.append(compute(conn, row["id"]))
    return sorted(out, key=lambda x: x["score"], reverse=True)
