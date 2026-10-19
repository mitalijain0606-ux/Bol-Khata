import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { speak, startListening, stopSpeaking, speechSupported, startRecording, transcribeViaPrisma } from "../voice.js";

const LANGS = [
  { code: "hi-IN", label: "हिंदी", ex: "Sharma ji ko do hazaar ka udhaar lagana" },
  { code: "mr-IN", label: "मराठी", ex: "राजेश शर्मा ला 2,000 चा उधार लावा" },
  { code: "ta-IN", label: "தமிழ்", ex: "ராஜேஷ் 2,000 கடன் பதிவு செய்" },
];

export default function Khata({ gnani, onNav }) {
  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState("");
  const [log, setLog] = useState([]);
  const [entries, setEntries] = useState([]);
  const [totals, setTotals] = useState(null);
  const [busy, setBusy] = useState(false);
  const [lang, setLang] = useState("hi-IN");
  const logRef = useRef(null);
  const recRef = useRef(null);

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
      const res = await api.command(text, lang); // rule brain; Evon upgrades this server-side
      say(res.reply, "agent");
      speak(res.reply, { lang, pitch: 1, rate: 1.02 });
      if (["ENTRY_ADDED", "SETTLED"].includes(res.action)) refreshFeed();
    } catch (e) {
      say("Server se baat nahi ho payi — backend chal raha hai?", "agent");
    }
    setBusy(false);
  };

  const toggleMic = () => {
    // stop-path: recording chal rahi hai -> roko aur Prisma ko bhejo
    if (recRef.current) {
      const r = recRef.current;
      recRef.current = null;
      setListening(false);
      setHeard("Sun raha hoon…");
      r.stop()
        .then((wav) => transcribeViaPrisma(wav, lang))
        .then((d) => {
          if (d.transcript) processUtterance(d.transcript);
          else { setHeard(""); say("Awaz clear nahi aayi — dobara boliye.", "agent"); }
        })
        .catch((e) => { setHeard(""); say("STT fail: " + e.message, "agent"); });
      return;
    }

    stopSpeaking();
    if (gnani && navigator.mediaDevices?.getUserMedia) {
      // Gnani Mode: mic -> Prisma
      setListening(true);
      setHeard("sun raha hoon… (bol ke dobara dabaao)");
      startRecording()
        .then((r) => { recRef.current = r; })
        .catch((e) => { setListening(false); setHeard(""); say("Mic nahi khula: " + e.message, "agent"); });
      return;
    }

    // Mock Mode: browser speech recognition
    if (!speechSupported()) {
      say("Is browser me mic-sunne ki suvidha nahi — Chrome ya Edge use kariye.", "agent");
      return;
    }
    setListening(true);
    setHeard("sun raha hoon...");
    startListening(
      (partial) => setHeard(partial),
      (final) => {
        setListening(false);
        if (final) processUtterance(final);
        else setHeard("");
      },
      lang
    );
  };

  return (
    <>
      <div className="card mic-card">
        <div className="row">
          <div className="stat">
            <div className="num red">{totals ? fmt(totals.udhaar_total) : "—"}</div>
            <div className="lbl">Kul udhaar</div>
          </div>
          <div className="stat">
            <div className="num green">{totals ? fmt(totals.cash_in_today) : "—"}</div>
            <div className="lbl">Aaj cash aaya</div>
          </div>
          <div className="stat">
            <div className="num amber">{totals ? fmt(totals.udhaar_today) : "—"}</div>
            <div className="lbl">Aaj udhaar</div>
          </div>
        </div>

        <div className="lang-row">
          {LANGS.map((l) => (
            <button key={l.code}
                    className={"lang-chip" + (lang === l.code ? " active" : "")}
                    onClick={() => setLang(l.code)}>
              {l.label}
            </button>
          ))}
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
              <button className="btn ghost" style={{ margin: 5, padding: "8px 12px", fontSize: 12.5 }}
                      onClick={() => processUtterance(LANGS.find(l => l.code === lang).ex)}>
                “{LANGS.find(l => l.code === lang).ex}”
              </button>
              {lang === "hi-IN" && (
                <>
                  <button className="btn ghost" style={{ margin: 5, padding: "8px 12px", fontSize: 12.5 }}
                          onClick={() => processUtterance("Gupta ji ne paanch sau diye")}>
                    “Gupta ji ne paanch sau diye”
                  </button>
                  <button className="btn ghost" style={{ margin: 5, padding: "8px 12px", fontSize: 12.5 }}
                          onClick={() => processUtterance("Verma ji ka kitna baki hai")}>
                    “Verma ji ka kitna baki hai”
                  </button>
                  <button className="btn ghost" style={{ margin: 5, padding: "8px 12px", fontSize: 12.5 }}
                          onClick={() => processUtterance("Aaj ka hisaab")}>
                    “Aaj ka hisaab”
                  </button>
                </>
              )}
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
