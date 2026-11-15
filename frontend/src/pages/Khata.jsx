import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import CustomerDetail from "./CustomerDetail.jsx";
import { fmt } from "../util.js";
import { Icon, useCountUp } from "../icons.jsx";
import { speak, startListening, stopListening, stopSpeaking, speechSupported, startRecording, transcribeViaCloud } from "../voice.js";

const LANGS = [
  { code: "hi-IN", label: "Hinglish", ex: "Sharma ji ko do hazaar ka udhaar lagana" },
  { code: "mr-IN", label: "मराठी", ex: "राजेश शर्मा ला 2,000 चा उधार लावा" },
  { code: "ta-IN", label: "தமிழ்", ex: "ராஜேஷ் 2,000 கடன் பதிவு செய்" },
];

const ADVICE = { yes: "✅ De sakte hain", careful: "⚠️ Sambhal ke", no: "⛔ Mat dijiye" };

export default function Khata({ gnani, onNav, me }) {
  const [typed, setTyped] = useState("");
  const [openCid, setOpenCid] = useState(null);
  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState("");
  const [log, setLog] = useState([]);
  const [entries, setEntries] = useState([]);
  const [totals, setTotals] = useState(null);
  const [busy, setBusy] = useState(false);
  const [lang, setLang] = useState("hi-IN");
  const logRef = useRef(null);
  const owed = useCountUp(totals ? (totals.outstanding ?? totals.udhaar_total) : null);
  const cashToday = useCountUp(totals ? totals.cash_in_today : null);
  const udhaarToday = useCountUp(totals ? totals.udhaar_today : null);
  const recRef = useRef(null);

  const refreshFeed = () => {
    api.entries(12).then(setEntries).catch(() => {});
    api.totals().then(setTotals).catch(() => {});
  };
  useEffect(() => {
    refreshFeed();
    return () => { stopListening(); stopSpeaking(); };   // leaving the tab: release the mic
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: 1e6, behavior: "smooth" });
  }, [log]);

  const say = (text, who = "agent", extra = {}) => setLog((l) => [...l, { who, text, ...extra }]);

  const processUtterance = async (text) => {
    if (!text) return;
    setHeard("");
    setBusy(true);
    say(text, "you");
    try {
      const res = await api.command(text, lang); // LLM agent when configured; rules for risky intents and fallback
      say(res.reply, "agent", {
        confirm: res.action === "CONFIRM_SETTLE",
        advice: res.action === "LEND_ADVICE" ? res.data.decision : null,
      });
      speak(res.reply, { lang, pitch: 1, rate: 1.02 });
      if (["ENTRY_ADDED", "SETTLED", "ENTRY_DELETED"].includes(res.action)) refreshFeed();
    } catch (e) {
      if (e.message !== "logged out") say("Server se baat nahi ho payi — backend chal raha hai?", "agent");
    }
    setBusy(false);
  };

  const toggleMic = () => {
    // stop-path: recording chal rahi hai -> roko aur cloud STT ko bhejo
    if (recRef.current) {
      const r = recRef.current;
      recRef.current = null;
      setListening(false);
      setHeard("Sun raha hoon…");
      r.stop()
        .then((wav) => transcribeViaCloud(wav, lang))
        .then((d) => {
          if (d.transcript) processUtterance(d.transcript);
          else { setHeard(""); say("Awaz clear nahi aayi — dobara boliye.", "agent"); }
        })
        .catch((e) => { setHeard(""); say("STT fail: " + e.message, "agent"); });
      return;
    }

    // Mock Mode stop-path: second tap ends listening (whatever was heard is used)
    if (listening) {
      stopListening();
      return;
    }

    stopSpeaking();
    if (gnani && navigator.mediaDevices?.getUserMedia) {
      // cloud mode: mic -> cloud STT
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
      (final, err) => {
        setListening(false);
        if (final) processUtterance(final);
        else {
          setHeard("");
          say(err ? err.message : "Kuch sunai nahi diya — mic dabake dobara boliye.", "agent");
        }
      },
      lang
    );
  };

  return (
    <>
      <div className="card mic-card">
        <div className="row">
          <div className="stat">
            <div className="num red">{owed != null ? fmt(owed) : "—"}</div>
            <div className="lbl">Kul baki udhaar</div>
          </div>
          <div className="stat">
            <div className="num green">{cashToday != null ? fmt(cashToday) : "—"}</div>
            <div className="lbl">Aaj cash aaya</div>
          </div>
          <div className="stat">
            <div className="num amber">{udhaarToday != null ? fmt(udhaarToday) : "—"}</div>
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
          <button className={"mic-orb" + (listening ? " listening" : busy ? " thinking" : "")}
                  onClick={toggleMic} disabled={busy} aria-label={listening ? "Sunna band karo" : "Bolo"}>
            <Icon name={listening ? "stop" : "mic"} size={42} stroke={2} />
          </button>
          <div className={"wave" + (listening ? " on" : "")} aria-hidden="true">
            {Array.from({ length: 11 }, (_, i) => <i key={i} />)}
          </div>
          <div className="mic-hint">
            {listening ? <span><span className="speaking-dot" />bolo, main likh raha hoon…</span>
              : busy ? "soch raha hoon…" : "dabake boliye — entry, sawaal, ya hisaab"}
          </div>
          <div className="heard">{heard}</div>
        </div>

        {/* typed fallback: same brain, no mic needed (noisy room, no permission, Firefox) */}
        <form className="say-row" onSubmit={(e) => {
          e.preventDefault();
          const t = typed.trim();
          if (!t || busy) return;
          setTyped("");
          stopSpeaking();
          processUtterance(t);
        }}>
          <input value={typed} onChange={(e) => setTyped(e.target.value)}
                 placeholder="…ya yahan likh kar bhejiye" aria-label="Likh kar boliye" />
          <button className="btn" disabled={busy || !typed.trim()}>Bhejo</button>
        </form>
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
                  <button className="btn ghost" style={{ margin: 5, padding: "8px 12px", fontSize: 12.5 }}
                          onClick={() => processUtterance("Chauhan ji ko 2000 udhaar du kya")}>
                    “Chauhan ji ko 2000 udhaar du kya?”
                  </button>
                </>
              )}
            </div>
          )}
          {log.map((m, i) => (
            <div key={i} className={`bubble ${m.who === "you" ? "you" : "agent"}`}>
              <span className="who">{m.who === "you" ? "Aap" : "Bol-Khata"}</span>
              {m.advice && <><span className={"advice " + m.advice}>{ADVICE[m.advice]}</span><br /></>}
              {m.text}
              {m.confirm && i === log.length - 1 && (
                <div className="chip-row">
                  <button className="btn" style={{ padding: "8px 16px" }} disabled={busy}
                          onClick={() => processUtterance("haan")}>Haan, clear karo</button>
                  <button className="btn ghost" style={{ padding: "8px 16px" }} disabled={busy}
                          onClick={() => processUtterance("nahi")}>Nahi</button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>Aakhri entries</h3>
        {entries.length > 0 && (
          <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 4 }}>
            Entry pe tap karo — poora khata, galat entry hatana, WhatsApp reminder.
          </div>
        )}
        {entries.length === 0 && <div className="empty">Abhi koi entry nahi.</div>}
        {entries.map((e) => (
          <div key={e.id} className={"entry tap " + (e.type === "UDHAAR" ? "udhaar" : "payment")}
               onClick={() => setOpenCid(e.customer_id)}>
            <div className="tag"><Icon name={e.type === "UDHAAR" ? "up" : "down"} size={19} stroke={2.2} /></div>
            <div className="meta">
              <b>{e.customer_name}</b>
              <span>{e.items_text || e.raw_transcript || "—"}</span>
            </div>
            <div className="amt">{e.type === "UDHAAR" ? "+" : "−"}{fmt(e.amount)}</div>
          </div>
        ))}
      </div>

      <button className="btn" onClick={() => onNav("call")}>📞 Vasooli call shuru karo</button>

      {openCid && (
        <CustomerDetail cid={openCid} me={me} onClose={() => setOpenCid(null)} onChanged={refreshFeed} />
      )}
    </>
  );
}

export { fmt };
