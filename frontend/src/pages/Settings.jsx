import React, { useState } from "react";
import { api } from "../api.js";
import { recordClip, speechSupported } from "../voice.js";

export default function Settings({ me, onSaved, onLogout }) {
  const [enrollState, setEnrollState] = useState("");
  const [busy, setBusy] = useState(false);

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
      const res = await api.enroll(me.id, blob);
      setEnrollState(
        res.ok
          ? "✅ Ho gaya! Ab sirf aapki awaaz ledger badal sakti hai."
          : "⚠️ Voice-lock library backend pe install nahi — abhi offline hai."
      );
      onSaved && onSaved();
    } catch (e) {
      setEnrollState("Recording fail: " + e.message);
    }
    setBusy(false);
  };

  return (
    <>
      <h2 className="pagetitle">Setting</h2>

      <div className="card">
        <h3>Mera account</h3>
        <div className="prov"><span>Naam</span><span>{me?.name || "—"}</span></div>
        <div className="prov"><span>Dukaan</span><span>{me?.shop_name || "—"}</span></div>
        <div className="prov"><span>Mobile</span><span>{me?.phone || "—"}</span></div>
        <div className="prov"><span>Voice lock</span>
          <span className={me?.voice_enrolled ? "on" : "off"}>{me?.voice_enrolled ? "Set hai ✅" : "Set nahi"}</span></div>
      </div>

      <div className="card">
        <h3>Awaaz ka lock</h3>
        <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 10 }}>
          Apni awaaz enroll karo — uske baad entries delete/settle sirf aapki awaaz
          bolke hongi. Customer ki awaaz se kuch nahi badlega.
        </div>
        <button className="btn" onClick={enroll} disabled={busy}>
          {busy ? "record ho raha hai…" : "🎙️ Meri awaaz enroll karo (5 sec)"}
        </button>
        {enrollState && <div style={{ marginTop: 10, fontSize: 13 }}>{enrollState}</div>}
      </div>

      <button className="btn ghost" style={{ width: "100%", color: "var(--red)" }} onClick={onLogout}>
        Logout
      </button>
    </>
  );
}
