"""End-to-end smoke tests — no extra dependencies, uses a throw-away database.

    cd backend
    .venv/bin/python -m unittest tests.test_smoke -v        (Windows: .venv\\Scripts\\python ...)
"""
import logging
import os
import tempfile
import unittest
from datetime import date, timedelta

os.environ["BOLKHATA_DATA_DIR"] = tempfile.mkdtemp(prefix="bolkhata-test-")
for k in ("SPEECH_API_KEY", "EVON_API_URL", "EVON_HF_MODEL"):
    os.environ[k] = ""          # tests always run in free/mock mode

logging.disable(logging.INFO)

from fastapi.testclient import TestClient  # noqa: E402

from app.agent import nlu, tools as T  # noqa: E402
from app.db import db  # noqa: E402
from app.main import app  # noqa: E402
from scripts.seed_fake_data import seed  # noqa: E402


class NLU(unittest.TestCase):
    names = ["Rajesh Sharma", "Suresh Gupta", "Mahesh Verma", "Dinesh Yadav"]

    def check(self, text, lang, intent, amount=None, name=None):
        t = nlu.transliterate(text)
        self.assertEqual(nlu.classify(t, lang), intent, t)
        if amount is not None:
            self.assertEqual(nlu.parse_amount(t, lang), amount, t)
        if name is not None:
            self.assertEqual(nlu.find_customer_name(t, self.names), name, t)

    def test_roman_hinglish(self):
        self.check("Sharma ji ko do hazaar paanch sau ka udhaar lagana", "hi-IN", "ADD_UDHAAR", 2500, "Rajesh Sharma")
        self.check("Sharma ji ne paanch sau diye", "hi-IN", "PAYMENT", 500, "Rajesh Sharma")
        self.check("Yadav ji ne 1200 rupaye jama kiye", "hi-IN", "PAYMENT", 1200, "Dinesh Yadav")
        self.check("Verma ji ka kitna baki hai", "hi-IN", "QUERY_BALANCE", None, "Mahesh Verma")
        self.check("Sharma ji ka hisaab clear kar do", "hi-IN", "SETTLE", None, "Rajesh Sharma")
        self.check("aaj ka hisaab", "hi-IN", "BRIEFING", None, "")
        self.check("Gupta ji ko dedh sau ka udhaar likh do", "hi-IN", "ADD_UDHAAR", 150)
        self.check("Gupta ji ka do sau ka udhaar likh do", "hi-IN", "ADD_UDHAAR", 200)
        self.check("ek lakh bees hazaar", "hi-IN", "UNKNOWN", 120000)
        self.check("Verma ji ko dhai hazaar ka udhaar lagao", "hi-IN", "ADD_UDHAAR", 2500)

    def test_devanagari_hindi(self):
        # this is what the browser's hi-IN speech recognition returns
        self.check("शर्मा जी को दो हजार का उधार लगाना", "hi-IN", "ADD_UDHAAR", 2000, "Rajesh Sharma")
        self.check("शर्मा जी को दो हज़ार पाँच सौ का उधार लगाना", "hi-IN", "ADD_UDHAAR", 2500, "Rajesh Sharma")
        self.check("शर्मा जी को ₹2000 का उधार लगाना", "hi-IN", "ADD_UDHAAR", 2000)
        self.check("गुप्ता जी ने पांच सौ दिए", "hi-IN", "PAYMENT", 500, "Suresh Gupta")
        self.check("वर्मा जी का कितना बाकी है", "hi-IN", "QUERY_BALANCE", None, "Mahesh Verma")
        self.check("आज का हिसाब", "hi-IN", "BRIEFING")
        self.check("शर्मा जी का हिसाब क्लियर कर दो", "hi-IN", "SETTLE", None, "Rajesh Sharma")
        self.check("यादव जी को तीन सौ बीस का उधार लिख दो", "hi-IN", "ADD_UDHAAR", 320, "Dinesh Yadav")

    def test_marathi_tamil(self):
        self.check("राजेश शर्मा ला 2,000 चा उधार लावा", "mr-IN", "ADD_UDHAAR", 2000, "Rajesh Sharma")
        self.check("राजेश शर्मा ने 500 दिले", "mr-IN", "PAYMENT", 500, "Rajesh Sharma")
        self.check("ராஜேஷ் 2,000 கடன் பதிவு செய்", "ta-IN", "ADD_UDHAAR", 2000, "Rajesh Sharma")
        self.check("ராஜேஷ் 500 கொடுத்தார்", "ta-IN", "PAYMENT", 500, "Rajesh Sharma")

    def test_due_dates(self):
        today = date.today()
        iso = lambda n: (today + timedelta(days=n)).isoformat()
        self.assertEqual(T.parse_due_date("kal de dunga"), iso(1))
        self.assertEqual(T.parse_due_date("parso pakka"), iso(2))
        self.assertEqual(T.parse_due_date("bilkul, aajkal mandi hai"), iso(1))   # no false 'kal'/'aaj'
        d = date.fromisoformat(T.parse_due_date("31 tareekh"))
        self.assertEqual(d.day, 31)
        self.assertGreaterEqual(d, today)


class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed()
        cls.c = TestClient(app)
        cls.c.__enter__()
        tok = cls.c.post("/api/auth/login", json={"phone": "9876543210", "password": "demo1234"}).json()["token"]
        cls.demo = {"Authorization": f"Bearer {tok}"}
        tok2 = cls.c.post("/api/auth/register", json={
            "name": "Naya", "shop_name": "Nayi Dukaan", "phone": "9000000001", "password": "abcd"}).json()["token"]
        cls.other = {"Authorization": f"Bearer {tok2}"}

    @classmethod
    def tearDownClass(cls):
        cls.c.__exit__(None, None, None)

    def say(self, text, who=None, lang="hi-IN"):
        r = self.c.post("/api/voice/command", json={"text": text, "lang": lang}, headers=who or self.demo)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_auth_required(self):
        for path in ("/api/customers", "/api/totals", "/api/entries", "/api/briefing", "/api/trust-scores"):
            self.assertEqual(self.c.get(path).status_code, 401, path)
        self.assertEqual(self.c.post("/api/auth/login", json={"phone": "9876543210", "password": "x"}).status_code, 401)
        self.assertEqual(self.c.get("/api/health").status_code, 200)
        self.assertEqual(self.c.get("/api/tts?text=hi").status_code, 204)

    def test_accounts_are_isolated(self):
        demo_before = self.c.get("/api/totals", headers=self.demo).json()
        self.assertEqual(self.c.get("/api/customers", headers=self.other).json(), [])
        brief = self.c.get("/api/briefing", headers=self.other).json()
        self.assertEqual(brief["data"]["promises_due"], [])
        self.say("Sharma ji ko 500 ka udhaar lagana", self.other)
        r = self.say("Sharma ji ka hisaab clear kar do", self.other)
        self.assertEqual(r["action"], "CONFIRM_SETTLE")      # asks before wiping a balance
        r = self.say("हाँ", self.other)
        self.assertEqual(r["action"], "SETTLED")
        self.assertIn("₹500", r["reply"])
        self.assertEqual(self.c.get("/api/totals", headers=self.demo).json(), demo_before)
        demo_cid = self.c.get("/api/customers", headers=self.demo).json()[0]["id"]
        self.assertEqual(self.c.get(f"/api/customers/{demo_cid}/ledger", headers=self.other).status_code, 404)
        self.assertEqual(self.c.post(f"/api/call/start/{demo_cid}", headers=self.other).status_code, 404)

    def test_voice_ledger_flow(self):
        before = self.c.get("/api/totals", headers=self.demo).json()["outstanding"]
        r = self.say("मिश्रा जी को दो हजार का उधार लगाना")
        self.assertEqual((r["action"], r["data"]["amount"], r["data"]["customer"]), ("ENTRY_ADDED", 2000, "Ramesh Mishra"))
        r = self.say("Mishra ji ne paanch sau diye")
        self.assertEqual((r["action"], r["data"]["kind"], r["data"]["amount"]), ("ENTRY_ADDED", "PAYMENT", 500))
        after = self.c.get("/api/totals", headers=self.demo).json()["outstanding"]
        self.assertEqual(after, before + 1500)
        self.assertEqual(self.say("Mishra ji ka kitna baki hai")["action"], "BALANCE")
        self.assertEqual(self.say("kitna udhaar bana total")["action"], "TOTALS")
        self.assertEqual(self.say("aaj ka hisaab")["action"], "BRIEFING")
        self.assertEqual(self.say("Kapoor ji ne 200 diye")["action"], "NOT_FOUND")   # payment never invents a customer

    def test_settle_needs_confirmation(self):
        self.say("Confirm ji ko 700 ka udhaar lagana")
        self.assertEqual(self.say("Confirm ji ka hisaab clear kar do")["action"], "CONFIRM_SETTLE")
        self.assertEqual(self.say("nahi")["action"], "CANCELLED")
        self.assertIn("₹700", self.say("Confirm ji ka kitna baki hai")["reply"])
        self.say("Confirm ji ka hisaab clear kar do")
        self.assertEqual(self.say("Confirm ji ka kitna baki hai")["action"], "BALANCE")   # other command drops it
        self.assertEqual(self.say("haan")["action"], "UNKNOWN")

    def test_undo_and_delete(self):
        self.say("Bansal ji ko 400 ka udhaar lagana")
        self.say("Bansal ji ko 999 ka udhaar lagana")
        r = self.say("galat entry hatao")
        self.assertEqual((r["action"], r["data"]["amount"], r["data"]["balance"]), ("ENTRY_DELETED", 999, 400))
        eid = self.c.get("/api/entries?limit=1", headers=self.demo).json()[0]["id"]
        self.assertEqual(self.c.delete(f"/api/entries/{eid}", headers=self.other).status_code, 404)
        self.assertEqual(self.c.delete(f"/api/entries/{eid}", headers=self.demo).json()["balance"], 0)

    def test_lend_advice(self):
        r = self.say("Sharma ji ko 2000 udhaar du kya")
        self.assertEqual((r["action"], r["data"]["decision"], r["data"]["amount"]), ("LEND_ADVICE", "yes", 2000))
        self.assertEqual(self.say("चौहान जी को 500 उधार दूं क्या")["data"]["decision"], "no")
        self.assertEqual(self.say("Naya Banda ko udhaar dena chahiye")["data"]["decision"], "careful")
        before = self.c.get("/api/totals", headers=self.demo).json()
        self.assertEqual(self.c.get("/api/totals", headers=self.demo).json(), before)   # advice writes nothing
        self.assertEqual(self.say("Sharma ji ko 100 ka udhaar de do")["action"], "ENTRY_ADDED")  # "de do" is not a question

    def test_promise_lifecycle(self):
        self.say("Lifecycle ji ko 2000 ka udhaar lagana")
        cid = next(c["id"] for c in self.c.get("/api/customers", headers=self.demo).json() if c["name"] == "Lifecycle")
        with db() as conn:
            T.log_promise(conn, cid, 1000, (date.today() + timedelta(days=2)).isoformat())
            T.log_promise(conn, cid, 300, (date.today() - timedelta(days=1)).isoformat())  # already overdue
            conn.execute("UPDATE promise SET created_at = datetime('now', 'localtime', '-1 day') "
                         "WHERE customer_id = ?", (cid,))
        post = lambda amt: self.c.post("/api/entries", headers=self.demo,
                                       json={"customer_id": cid, "type": "PAYMENT", "amount": amt})
        status = lambda: [p["status"] for p in self.c.get(
            f"/api/customers/{cid}/ledger", headers=self.demo).json()["promises"]][::-1]
        self.assertEqual(post(0).status_code, 400)
        self.assertEqual(post(100).status_code, 200)
        self.assertEqual(status()[0], "PENDING")          # ₹100 does not keep a ₹1,000 promise
        self.c.get("/api/trust-scores", headers=self.demo)
        self.assertEqual(status()[1], "BROKEN")           # due date passed
        self.assertEqual(self.say("Lifecycle ji ne 900 diye")["action"], "ENTRY_ADDED")
        self.assertEqual(status()[0], "KEPT")             # 100 + 900 covers it

    def test_collections_call(self):
        custs = [c for c in self.c.get("/api/customers", headers=self.demo).json() if c["balance"] > 0]
        for persona in ("promiser", "avoider", "bargainer"):
            cust = next(c for c in custs if c["persona"] == persona)
            start = self.c.post(f"/api/call/start/{cust['id']}", headers=self.demo).json()
            cid = start["call_id"]
            self.assertEqual(self.c.post(f"/api/call/{cid}/step", headers=self.other).status_code, 404)
            for _ in range(10):
                s = self.c.post(f"/api/call/{cid}/step", headers=self.demo).json()
                if s["done"]:
                    break
            self.assertTrue(s["done"], persona)
            end = self.c.post(f"/api/call/{cid}/end", headers=self.demo).json()
            self.assertIn(end["outcome"], ("PROMISE", "PARTIAL"), persona)
            self.assertGreaterEqual(end["promise"]["due_date"], date.today().isoformat())
            led = self.c.get(f"/api/customers/{cust['id']}/ledger", headers=self.demo).json()
            self.assertEqual(led["promises"][0]["status"], "PENDING")
            if end["partial_today"]:
                self.assertAlmostEqual(led["balance"], cust["balance"] - end["partial_today"], places=2)
                self.assertAlmostEqual(led["promises"][0]["amount"], led["balance"], places=2)
            self.assertEqual(self.c.post(f"/api/call/{cid}/end", headers=self.demo).status_code, 404)

    def test_trust_scores(self):
        scores = self.c.get("/api/trust-scores", headers=self.demo).json()
        self.assertGreaterEqual(len(scores), 12)
        self.assertTrue(all(0 <= s["score"] <= 100 for s in scores))
        self.assertGreater(len({s["band"] for s in scores}), 1)     # a real spread, not all one band

    def test_new_customer_is_not_pakka(self):
        self.say("Navin ji ko 250 ka udhaar likh do")
        s = next(x for x in self.c.get("/api/trust-scores", headers=self.demo).json() if x["customer"] == "Navin")
        self.assertEqual((s["band"], s["score"]), ("Naya", 60))
        self.assertEqual(self.say("Navin ji ko 1000 udhaar du kya")["data"]["decision"], "careful")

    def test_tokens_cannot_be_forged_or_reused_after_expiry(self):
        from app import auth
        tok = auth.make_token(1)
        self.assertEqual(auth.sid_from_token(tok), 1)
        sid, exp, sig = tok.split(".")
        self.assertIsNone(auth.sid_from_token(f"2.{exp}.{sig}"))             # other account
        self.assertIsNone(auth.sid_from_token(f"1.{int(exp) + 999}.{sig}"))   # extended expiry
        self.assertIsNone(auth.sid_from_token(f"1.{sig}"))                    # old token format
        import hmac, hashlib
        old = f"1.{int(exp) - auth.TOKEN_TTL - 10}"
        old_sig = hmac.new(auth._secret(), old.encode(), hashlib.sha256).hexdigest()[:32]
        self.assertIsNone(auth.sid_from_token(f"{old}.{old_sig}"))            # expired

    def test_rate_limit(self):
        from app import main
        main._HITS.clear()
        for _ in range(15):
            self.c.post("/api/auth/login", json={"phone": "9999999999", "password": "x"})
        self.assertEqual(self.c.post("/api/auth/login", json={"phone": "9999999999", "password": "x"}).status_code, 429)
        main._HITS.clear()

    def test_voice_enroll_never_crashes(self):
        r = self.c.post("/api/shopkeeper/1/enroll", files={"file": ("a.wav", b"\\0" * 5000, "audio/wav")})
        self.assertEqual(r.status_code, 401)
        r = self.c.post("/api/shopkeeper/1/enroll", headers=self.other, files={"file": ("a.wav", b"\\0" * 5000, "audio/wav")})
        self.assertEqual(r.status_code, 403)
        r = self.c.post("/api/shopkeeper/1/enroll", headers=self.demo, files={"file": ("a.wav", b"\\0" * 5000, "audio/wav")})
        self.assertEqual(r.status_code, 200)
        self.assertIn("ok", r.json())


if __name__ == "__main__":
    unittest.main()


class LLMRouting(unittest.TestCase):
    """MOCKED LLM — no network. Checks our side of the contract only: the
    request shape Groq needs, and that risky intents never reach the LLM."""

    def setUp(self):
        import asyncio
        from app.agent import agent
        from app.speech import evon
        self.asyncio, self.agent, self.evon = asyncio, agent, evon
        self.calls = []

        async def fake_chat(messages, tools=None):
            self.calls.append({"messages": messages, "tools": tools})
            if tools:   # first turn: ask for a balance lookup
                return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "call_1", "type": "function",
                    "function": {"name": "query_balance", "arguments": '{"customer_name": "Sharma"}'}}]}}]}
            return {"choices": [{"message": {"role": "assistant", "content": "Sharma ji ka baki bata diya."}}]}

        self._orig_chat, self._orig_ready = evon.chat, agent.evon_settings_ready
        evon.chat = fake_chat
        agent.evon_settings_ready = lambda: True

    def tearDown(self):
        self.evon.chat, self.agent.evon_settings_ready = self._orig_chat, self._orig_ready

    def run_(self, text):
        return self.asyncio.run(self.agent.handle_utterance(text, "hi-IN", 1))

    def test_llm_handles_safe_intents_and_sends_tool_call_id(self):
        r = self.run_("Sharma ji ka kitna baki hai")
        self.assertEqual((r["brain"], r["action"]), ("llm", "BALANCE"))
        tool_msg = self.calls[1]["messages"][-1]
        self.assertEqual((tool_msg["role"], tool_msg["tool_call_id"]), ("tool", "call_1"))

    def test_risky_intents_stay_on_rules(self):
        for text, action in [("Sharma ji ka hisaab clear kar do", "CONFIRM_SETTLE"),
                             ("nahi", "CANCELLED"),
                             ("Sharma ji ko 2000 udhaar du kya", "LEND_ADVICE")]:
            r = self.run_(text)
            self.assertEqual((r["brain"], r["action"]), ("rules", action), text)
        self.assertEqual(self.calls, [])          # the LLM was never asked

    def test_groq_payload_hides_reasoning_with_tools(self):
        import httpx
        from app.config import settings
        sent = {}

        class FakeClient:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def post(self, url, headers=None, json=None):
                sent.update(json)
                return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]},
                                      request=httpx.Request("POST", url))

        orig_client, orig_url = self.evon.httpx.AsyncClient, settings.evon_api_url
        self.evon.httpx.AsyncClient, settings.evon_api_url = FakeClient, "https://api.groq.com/openai/v1/chat/completions"
        try:
            self.asyncio.run(self._orig_chat([{"role": "user", "content": "hi"}], tools=[{"name": "x", "parameters": {}}]))
        finally:
            self.evon.httpx.AsyncClient, settings.evon_api_url = orig_client, orig_url
        self.assertEqual(sent["reasoning_format"], "hidden")
        self.assertEqual(sent["tools"][0]["type"], "function")
