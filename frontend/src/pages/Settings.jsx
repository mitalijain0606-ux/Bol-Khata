import React, { useState } from "react";
import { api } from "../api.js";
import { recordClip, speechSupported } from "../voice.js";

export default function Settings({ health, shop, onSaved }) {
  const [enrollState, setEnrollState] = useState("");
  const [busy, setBusy] = useState(false);

  const prov = health?.providers || {};

  const enroll = async () => {
    if (!speechSupported()) {
      setEnrollState("Mic recording ke liye Chrome use karo.");
      return;
    }
    setBusy(true);
    setEnrollState("Boliye: 'Bol-Khata mera khata hai…' (5 second)");
    try {
      const blob = await recordClip(5000);
      setEnrollState("Awaaz ka finger-print ban raha hai…");
      const res = await api.enroll(1, blob);
      setEnrollState(
        res.ok
          ? "✅ Ho gaya! Ab sirf aapki awaaz ledger badal sakti hai."
          : "⚠️ Voice-lock library backend pe install nahi (pip install speechbrain torchaudio) — abhi offline hai."
      );
      onSaved && onSaved();
    } catch (e) {
      setEnrollState("Recording fail: " + e.message);
    }
    setBusy(false);
  };

  return (
    <>
      <h2 className="pagetitle">Settings</h2>

      <div className="card">
        <h3>Dukaan</h3>
        <div className="field">
          <label>Malik</label>
          <input value={shop?.name || ""} readOnly />
        </div>
        <div className="field">
          <label>Dukaan ka naam</label>
          <input value={shop?.shop_name || ""} readOnly />
        </div>
      </div>

      <div className="card">
        <h3>Awaaz ka lock</h3>
        <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 10 }}>
          Apni awaaz enroll karo — phir entries delete/settle sirf aapki awaaz pe hongi.
          Customer ki awaaz se kuch nahi badlega.
        </div>
        <button className="btn" onClick={enroll} disabled={busy}>
          {busy ? "record ho raha hai…" : "🎙️ Meri awaaz enroll karo (5 sec)"}
        </button>
        {enrollState && <div style={{ marginTop: 10, fontSize: 13 }}>{enrollState}</div>}
      </div>

      <div className="card">
        <h3>AI Providers — Mode: {health?.mode || "…"}</h3>
        <div className="prov"><span>Gnani Prisma v2.5 (STT)</span><span className={prov.stt_prisma ? "on" : "off"}>{prov.stt_prisma ? "ACTIVE" : "mock (browser STT)"}</span></div>
        <div className="prov"><span>Gnani Timbre v2.5 (TTS)</span><span className={prov.tts_timbre ? "on" : "off"}>{prov.tts_timbre ? "ACTIVE" : "mock (browser TTS)"}</span></div>
        <div className="prov"><span>Gnani Evon v3.3 (reasoning)</span><span className={prov.evon ? "on" : "off"}>{prov.evon ? "ACTIVE" : "rules engine"}</span></div>
        <div className="prov"><span>Voice lock (ECAPA-TDNN)</span><span className={prov.voice_lock ? "on" : "off"}>{prov.voice_lock ? "READY" : "off"}</span></div>
        <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 10 }}>
          Gnani pe shift: backend/.env me GNANI_API_KEY_ID + endpoint paths bharo
          (docs.gnani.ai quickstart se) → restart → yahan sab ACTIVE dikh jayega.
          Code same rehta hai, sirf providers switch hote hain.
        </div>
      </div>

      <div className="card" style={{ fontSize: 12.5, color: "var(--muted)" }}>
        ⚠️ Privacy: is demo ka saara data synthetic hai — fake naam, fake numbers,
        banavati awaazein. DPDP Act ke hisaab se koi real personal data use nahi ho raha.
      </div>
    </>
  );
}
