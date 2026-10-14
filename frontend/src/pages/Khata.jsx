import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { speak, startListening, stopSpeaking, speechSupported } from "../voice.js";

const EXAMPLES = [
  "Sharma ji ko do hazaar ka udhaar lagana",
  "Gupta ji ne paanch sau diye",
  "Verma ji ka kitna baki hai",
  "Aaj ka hisaab",
];

export default function Khata({ gnani, onNav }) {
  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState("");
  const [log, setLog] = useState([]);
  const [entries, setEntries] = useState([]);
  const [totals, setTotals] = useState(null);
  const [busy, setBusy] = useState(false);
  const logRef = useRef(null);

  const refreshFeed = () => {
    api.entries(12).then(setEntries).catch(() => {});
    api.totals().then(setTotals).catch(() => {});
  };
  useEffect(refreshFeed, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: 1e6, behavior: "smooth" });
  }, [log]);

  const say = (text, who = "agent") => setLog((l) => [...l, { who, text }]);

  const processUtterance = async (text) => {
    if (!text) return;
    setHeard("");
    setBusy(true);
    say(text, "you");
    try {
      const res = await api.command(text); // rule brain; Evon upgrades this server-side
      say(res.reply, "agent");
      speak(res.reply, { pitch: 1, rate: 1.02 });
      if (["ENTRY_ADDED", "SETTLED"].includes(res.action)) refreshFeed();
    } catch (e) {
      say("Server se baat nahi ho payi — backend chal raha hai?", "agent");
    }
    setBusy(false);
  };

  const toggleMic = () => {
    if (listening) {
      setListening(false);
      return;
    }
    if (!speechSupported()) {
      say("Is browser me mic-sunne ki suvidha nahi — Chrome ya Edge use kariye.", "agent");
      return;
    }
    stopSpeaking();
    setListening(true);
    setHeard("sun raha hoon...");
    startListening(
      (partial) => setHeard(partial),
      (final) => {
        setListening(false);
        if (final) processUtterance(final);
        else setHeard("");
      },
      "hi-IN"
    );
  };

  return (
    <>
      <div className="card mic-card">
        <div className="row">
          <div className="stat">
            <div className="num amber">{totals ? fmt(totals.udhaar_total) : "—"}</div>
            <div className="lbl">Kul udhaar</div>
          </div>
          <div className="stat">
            <div className="num green">{totals ? fmt(totals.cash_in_today) : "—"}</div>
            <div className="lbl">Aaj cash aaya</div>
          </div>
          <div className="stat">
            <div className="num">{totals ? fmt(totals.udhaar_today) : "—"}</div>
            <div className="lbl">Aaj udhaar</div>
          </div>
        </div>

        <div className="mic-wrap">
          <button className={"mic-orb" + (listening ? " listening" : "")} onClick={toggleMic} disabled={busy}>
            {listening ? "◼" : "🎤"}
          </button>
          <div className="mic-hint">
            {listening ? <span><span className="speaking-dot" />bolo, main likh raha hoon…</span>
              : busy ? "soch raha hoon…" : "dabake boliye — entry, sawaal, ya hisaab"}
          </div>
          <div className="heard">{heard}</div>
        </div>
      </div>

      <div className="card">
        <h3>Baat-cheet</h3>
        <div className="log" ref={logRef}>
          {log.length === 0 && (
            <div className="empty">
              Mic dabao aur bolo. Jaise:<br />
              {EXAMPLES.map((e) => (
                <button key={e} className="btn ghost" style={{ margin: 5, padding: "8px 12px", fontSize: 12.5 }}
                        onClick={() => processUtterance(e)}>
                  “{e}”
                </button>
              ))}
            </div>
          )}
          {log.map((m, i) => (
            <div key={i} className={`bubble ${m.who === "you" ? "you" : "agent"}`}>
              <span className="who">{m.who === "you" ? "Aap" : "Bol-Khata"}</span>
              {m.text}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>Aakhri entries</h3>
        {entries.length === 0 && <div className="empty">Abhi koi entry nahi.</div>}
        {entries.map((e) => (
          <div key={e.id} className={"entry " + (e.type === "UDHAAR" ? "udhaar" : "payment")}>
            <div className="tag">{e.type === "UDHAAR" ? "📕" : "💰"}</div>
            <div className="meta">
              <b>{e.customer_name}</b>
              <span>{e.items_text || e.raw_transcript || "—"}</span>
            </div>
            <div className="amt">{e.type === "UDHAAR" ? "+" : "−"}{fmt(e.amount)}</div>
          </div>
        ))}
      </div>

      <button className="btn" onClick={() => onNav("call")}>📞 Vasooli call shuru karo</button>
    </>
  );
}

export const fmt = (n) =>
  "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
