import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { speak, stopSpeaking, startListening, speechSupported } from "../voice.js";
import { fmt, fmtDate, whatsappLink } from "../util.js";

const PERSONA_META = {
  promiser: { emoji: "🙂", label: "Pakka-wala" },
  avoider: { emoji: "😬", label: "Talne-wala" },
  bargainer: { emoji: "🤝", label: "Bhav-taai-wala" },
};

export default function CallScreen({ me, onNav }) {
  const [customers, setCustomers] = useState([]);
  const [call, setCall] = useState(null);      // {call_id, customer, balance, broken_count}
  const [bubbles, setBubbles] = useState([]);  // {who:'agent'|'customer', text}
  const [phase, setPhase] = useState("list");  // list | live | result
  const [speaking, setSpeaking] = useState("");
  const [result, setResult] = useState(null);
  const [stepBusy, setStepBusy] = useState(false);
  const logRef = useRef(null);
  const autoRef = useRef(true);
  const callIdRef = useRef(null);
  const custVoiceRef = useRef("Deepak");
  const stepLock = useRef(false);   // one step at a time (auto-advance + button share it)
  const endedRef = useRef(true);    // call finished / hung up -> late callbacks do nothing
  const [err, setErr] = useState("");
  const CUST_VOICES = ["Deepak", "Nalini", "Kaveri"];

  const loadCustomers = () =>
    api.customers().then((cs) => setCustomers(cs.filter((c) => c.balance > 0))).catch(() => {});

  useEffect(() => {
    loadCustomers();
    return () => {              // leaving the tab mid-call: stop talking, save what happened
      autoRef.current = false;
      stopSpeaking();
      if (!endedRef.current && callIdRef.current) {
        endedRef.current = true;
        api.callEnd(callIdRef.current).catch(() => {});
      }
    };
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: 1e6, behavior: "smooth" });
  }, [bubbles]);

  const push = (who, text) => setBubbles((b) => [...b, { who, text }]);

  const speakSeq = (who, text) =>
    new Promise((res) => {
      setSpeaking(who);
      // cloud TTS voices: agent = Poorvi (server default), customer = rotation
      // (pitch/rate only affect the browser-TTS fallback in mock mode)
      const gnaniVoice = who === "agent" ? "" : custVoiceRef.current;
      speak(text, {
        voice: gnaniVoice,
        pitch: who === "agent" ? 1 : 0.82,
        rate: who === "agent" ? 1.02 : 0.95,
        onEnd: () => setTimeout(() => { setSpeaking(""); res(); }, 250),
      });
      // safety: agar TTS fail ho jaye (silent browsers), 12s me aage badho
      setTimeout(() => res(), 12000);
    });

  const startCall = async (c) => {
    stopSpeaking();
    setErr("");
    let res;
    try {
      res = await api.callStart(c.id);
    } catch (e) {
      setErr("Call shuru nahi ho payi: " + e.message);
      return;
    }
    endedRef.current = false;
    stepLock.current = false;
    setStepBusy(false);
    setCall(res);
    callIdRef.current = res.call_id;
    custVoiceRef.current = CUST_VOICES[c.id % CUST_VOICES.length];
    setBubbles([]);
    setResult(null);
    setPhase("live");
    autoRef.current = true;
    push("agent", res.agent);
    await speakSeq("agent", res.agent);
    if (endedRef.current) return;
    push("customer", res.customer_line);
    await speakSeq("customer", res.customer_line);
    if (endedRef.current) return;
    autoAdvance();
  };

  const autoAdvance = async () => {
    // chalte-chalte poora negotiation chala do jab tak promise na ban jaye
    while (autoRef.current) {
      await new Promise((r) => setTimeout(r, 350));
      if (!autoRef.current) return;
      try {
        const ok = await doStep();
        if (!ok || ok.done) return;
      } catch (e) {
        return;
      }
    }
  };

  const doStep = async () => {
    if (!callIdRef.current || stepLock.current || endedRef.current) return null;
    stepLock.current = true;
    setStepBusy(true);
    try {
      const s = await api.callStep(callIdRef.current);
      if (endedRef.current) return null;
      push("agent", s.agent);
      await speakSeq("agent", s.agent);
      if (endedRef.current) return null;
      push("customer", s.customer);
      await speakSeq("customer", s.customer);
      if (endedRef.current) return null;
      if (s.done) {
        endedRef.current = true;
        autoRef.current = false;
        const end = await api.callEnd(callIdRef.current);
        showResult(end, s);
      }
      return s;
    } finally {
      stepLock.current = false;
      setStepBusy(false);
    }
  };

  const showResult = (end, lastStep) => {
    const promise = end.promise || lastStep?.promise || null;
    setResult({ ...end, promise });
    setPhase("result");
  };

  const shopkeeperSay = () => {
    if (!speechSupported()) {
      const t = prompt("Kya kehna hai customer ko?");
      if (t) bargeIn(t);
      return;
    }
    autoRef.current = false;      // aap bol rahe ho -> agent ruk jata hai
    stopSpeaking();
    startListening(
      null,
      (final) => { if (final) bargeIn(final); },
      "hi-IN"
    );
  };

  const bargeIn = async (text) => {
    if (!callIdRef.current || endedRef.current) return;
    autoRef.current = false;
    stopSpeaking();
    push("agent", "(aap) " + text);
    try {
      const r = await api.callSay(callIdRef.current, text);
      if (r.customer && !endedRef.current) {
        push("customer", r.customer);
        await speakSeq("customer", r.customer);
      }
    } catch (e) {
      setErr("Baat nahi pahunchi: " + e.message);
    }
  };

  const hangUp = async () => {
    autoRef.current = false;
    if (endedRef.current) return;
    endedRef.current = true;
    stopSpeaking();
    try {
      const end = await api.callEnd(callIdRef.current);
      showResult(end, {});
    } catch {
      setPhase("list");          // call already gone (server restart) — back to the list
      loadCustomers();
    }
  };

  // ---------- render ----------

  if (phase === "list") {
    return (
      <>
        <h2 className="pagetitle">Vasooli calls — kaun call karein?</h2>
        <div className="card">
          <h3>Udhaar baaki customers</h3>
          {err && <div className="auth-err">{err}</div>}
          {customers.length === 0 && <div className="empty">Sab ka hisaab clear hai! 🎉</div>}
          {[...customers]
            .sort((a, b) => b.balance - a.balance)
            .map((c) => {
              const pm = PERSONA_META[c.persona] || { emoji: "👤", label: "Customer" };
              return (
                <div key={c.id} className="score-row" onClick={() => startCall(c)}>
                  <div className="ring" style={{ "--ring-c": "var(--blue)", "--p": 70 }}><i>{pm.emoji}</i></div>
                  <div className="info">
                    <b>{c.name}</b>
                    <span>{pm.label} — call ke liye tap karo</span>
                  </div>
                  <div className="amt" style={{ color: "var(--red)", fontWeight: 700 }}>{fmt(c.balance)}</div>
                </div>
              );
            })}
        </div>
        <div className="card" style={{ fontSize: 12.5, color: "var(--muted)" }}>
          ℹ️ Ye customers <b>synthetic</b> hain (banavati awaaz + script) — challenge ke
          DPDP rule ke hisaab se koi real number call nahi hota. Agent negotiate karta hai,
          wada date leta hai, aur khata me likh deta hai.
        </div>
      </>
    );
  }

  if (phase === "live") {
    const pm = PERSONA_META[call.customer.persona] || { emoji: "👤", label: call.customer.persona_label };
    return (
      <>
        <div className="card">
          <div className={"call-ava" + (speaking === "customer" ? " ringing" : "")}>{pm.emoji}</div>
          <div className="call-name">{call.customer.name}</div>
          <div className="call-sub">
            <span className="pill persona">{pm.label}</span> &nbsp; Bakipada: <b style={{color:'var(--amber2)'}}>{fmt(call.balance)}</b>
            {call.broken_count > 0 && <> · ⚠️ {call.broken_count} wada toota</>}
          </div>
          <div className="call-sub">
            {speaking ? <span><span className="speaking-dot" />{speaking === "agent" ? "Bol-Khata bol raha hai…" : `${call.customer.name} bol raha hai…`}</span> : "…"}
          </div>
          <div className="log" ref={logRef} style={{ maxHeight: 260 }}>
            {bubbles.map((b, i) => (
              <div key={i} className={`bubble ${b.who === "customer" ? "agent" : "you"}`}>
                <span className="who">{b.who === "agent" ? "Bol-Khata (agent)" : b.who === "you" ? "Aap" : call.customer.name}</span>
                {b.text.replace("(malik) ", "")}
              </div>
            ))}
          </div>
          <div className="call-actions">
            <button className="btn ghost" onClick={shopkeeperSay}>🎤 Aap bolo</button>
            <button className="btn" onClick={doStep} disabled={stepBusy}>Aage badho →</button>
            <button className="btn danger" onClick={hangUp}>Cut karo</button>
          </div>
        </div>
      </>
    );
  }

  if (phase === "result" && result) {
    return (
      <div className="card result-card">
        <div style={{ fontSize: 44 }}>{result.partial_today ? "🤝" : result.promise ? "✅" : "❌"}</div>
        <div className="big">{result.summary}</div>
        {result.promise && (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>
            Wada khata me record ho gaya — {fmt(result.promise.amount)}, {fmtDate(result.promise.due_date)} tak.
            Date nikalne par ye apne aap "toda" mark hoga aur score girega.
          </div>
        )}
        {result.promise && call && (
          <a className="btn wa" style={{ marginTop: 12 }} target="_blank" rel="noreferrer"
             href={whatsappLink({ name: call.customer.name, shop: me?.shop_name || me?.name,
                                  balance: result.promise.amount, promise: result.promise })}>
            💬 Wade ka WhatsApp reminder bhejo
          </a>
        )}
        <div style={{ color: "var(--muted)", fontSize: 12.5, marginTop: 8 }}>
          Sentiment: {result.sentiment} · Outcome: {result.outcome}
        </div>
        <div className="call-actions">
          <button className="btn ghost" onClick={() => { setPhase("list"); setResult(null); loadCustomers(); }}>← Wapas list</button>
          <button className="btn green" onClick={() => onNav && onNav("khata")}>Khata dekho</button>
        </div>
      </div>
    );
  }

  return null;
}
