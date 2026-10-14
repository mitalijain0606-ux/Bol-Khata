"""Fake-data seeder — challenge rule: koi REAL data nahi (DPDP-safe).

Ek fake shopkeeper + 12 fake customers (3 personas) + 30 din ki entries +
wade (kuch poore, kuch tode) + purani calls, taaki Dashboard/Trust Score
pehle din se zinda dikhe.
"""
import random
from datetime import date, datetime, timedelta

from app.db import db, init_schema

FIRST = ["Sharma", "Gupta", "Verma", "Yadav", "Mishra", "Patel", "Singh",
         "Chauhan", "Mehta", "Joshi", "Rathod", "Desai"]
FIRST_NAMES = ["Rajesh", "Suresh", "Mahesh", "Dinesh", "Ramesh", "Jignesh",
               "Bhavesh", "Paresh", "Naresh", "Umesh", "Kamlesh", "Alok"]
ITEMS = ["chai, chini", "atta, dal", "tel, sabun", "chawal, masala",
         "doodh, biscuit", "namak, ghee", "supply (mahine ka)", "saman"]
PERSONAS = ["promiser", "avoider", "bargainer", "", "", "promiser",
            "avoider", "", "bargainer", "", "promiser", ""]


def seed(reset: bool = True):
    if reset:
        from pathlib import Path
        from app.config import DATA_DIR
        p = Path(DATA_DIR) / "bolkhata.db"
        if p.exists():
            p.unlink()
    init_schema()
    random.seed(42)
    today = date.today()

    with db() as conn:
        conn.execute("INSERT INTO shopkeeper (id, name, shop_name, language_pref) VALUES (1, 'Ramesh Kumar', 'Sharma Kirana Store', 'hi-IN')")

        customers = []
        for i in range(12):
            name = f"{FIRST_NAMES[i]} {FIRST[i]}"
            cur = conn.execute(
                "INSERT INTO customer (shopkeeper_id, name, phone, persona) VALUES (1, ?, ?, ?)",
                (name, f"98{random.randint(10000000, 99999999)}", PERSONAS[i]),
            )
            customers.append((cur.lastrowid, name))

        # risky customers (seed me score variety ke liye)
        RISKY = {4, 7, 11}

        for idx, (cid, name) in enumerate(customers):
            n_entries = random.randint(4, 9)
            risky = idx in RISKY
            for j in range(n_entries):
                days_ago = random.randint(35, 60) if risky else random.randint(0, 30)
                when = (today - timedelta(days=days_ago)).isoformat() + " 10:00:00"
                amount = random.choice([120, 250, 340, 480, 650, 900, 1200, 1500, 2200])
                conn.execute(
                    """INSERT INTO entry (shopkeeper_id, customer_id, type, amount, items_text, raw_transcript, status, created_at)
                       VALUES (1, ?, 'UDHAAR', ?, ?, ?, 'ACTIVE', ?)""",
                    (cid, amount, random.choice(ITEMS), f"{name} ko {amount} ka udhaar lagaya", when),
                )
                # risky customers ne shayad kabhi ek chhota payment kiya ho, der se
                if risky and random.random() < 0.6:
                    pay_when = (today - timedelta(days=max(0, days_ago - random.randint(18, 25)))).isoformat() + " 18:30:00"
                    conn.execute(
                        """INSERT INTO entry (shopkeeper_id, customer_id, type, amount, items_text, status, created_at)
                           VALUES (1, ?, 'PAYMENT', ?, '', 'ACTIVE', ?)""",
                        (cid, random.choice([100, 200, 300]), pay_when),
                    )
                # ~40% normal customers ne kabhi payment bhi kiya
                elif not risky and random.random() < 0.4 and days_ago > 5:
                    pay = random.choice([100, 200, 500, amount])
                    pay_when = (today - timedelta(days=max(0, days_ago - random.randint(2, 10)))).isoformat() + " 18:30:00"
                    conn.execute(
                        """INSERT INTO entry (shopkeeper_id, customer_id, type, amount, items_text, status, created_at)
                           VALUES (1, ?, 'PAYMENT', ?, '', 'ACTIVE', ?)""",
                        (cid, pay, pay_when),
                    )

            # wade: persona pe based
            persona = PERSONAS[customers.index((cid, name))]
            if persona == "promiser":
                for _ in range(random.randint(1, 2)):
                    conn.execute(
                        "INSERT INTO promise (customer_id, amount, due_date, status, created_at) VALUES (?, ?, ?, 'KEPT', ?)",
                        (cid, random.choice([500, 800, 1000]),
                         (today - timedelta(days=random.randint(2, 10))).isoformat(),
                         (today - timedelta(days=random.randint(10, 20))).isoformat()))
            elif persona == "avoider" or idx in RISKY:
                for _ in range(2 if idx in RISKY else 1):
                    conn.execute(
                        "INSERT INTO promise (customer_id, amount, due_date, status, created_at) VALUES (?, ?, ?, 'BROKEN', ?)",
                        (cid, random.choice([1000, 1500, 2000]),
                         (today - timedelta(days=random.randint(3, 8))).isoformat(),
                         (today - timedelta(days=random.randint(12, 25))).isoformat()))
            elif persona == "bargainer":
                conn.execute(
                    "INSERT INTO promise (customer_id, amount, due_date, status, created_at) VALUES (?, ?, ?, 'PENDING', ?)",
                    (cid, random.choice([700, 900]),
                     (today + timedelta(days=random.randint(1, 5))).isoformat(),
                     (today - timedelta(days=2)).isoformat()))

        # ek purani completed call record (dashboard me dikhe)
        conn.execute(
            """INSERT INTO call_record (customer_id, duration_sec, transcript, summary, sentiment, excuse_type, outcome, started_at)
               VALUES (?, 95, '[]', 'Test call record — seed data.', 'neutral', '', 'PROMISE', ?)""",
            (customers[0][0], (today - timedelta(days=1)).isoformat() + " 11:00:00"),
        )

    print("Seed done: 1 shopkeeper, 12 customers, entries, promises, 1 call.")


if __name__ == "__main__":
    seed()
