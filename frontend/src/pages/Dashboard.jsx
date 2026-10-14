import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { speak, stopSpeaking } from "../voice.js";
import { fmt } from "./Khata.jsx";

const RING_COLORS = { Pakka: "var(--green)", "Theek-thaak": "var(--amber)", "Sambhal ke": "var(--blue)", Risky: "var(--red)" };

export default function Dashboard({ onNav }) {
  const [brief, setBrief] = useState(null);
  const [scores, setScores] = useState([]);
  const [totals, setTotals] = useState(null);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api.briefing().then(setBrief).catch(() => {});
    api.trustScores().then(setScores).catch(() => {});
    api.totals().then(setTotals).catch(() => {});
    return () => stopSpeaking();
  }, []);

  const playBriefing = () => brief && speak(brief.reply, { pitch: 1, rate: 1 });

  const recovered = totals ? Math.max(0, totals.cash_in_total) : 0;

  return (
    <>
      <div className="card">
        <div className="row">
          <div className="stat">
            <div className="num amber">{totals ? fmt(totals.udhaar_total) : "—"}</div>
            <div className="lbl">Atka udhaar</div>
          </div>
          <div className="stat">
            <div className="num green">{totals ? fmt(totals.cash_in_total) : "—"}</div>
            <div className="lbl">Vasooli hui</div>
          </div>
        </div>
      </div>

      <div className="card briefing">
        <h3>Subah ki briefing</h3>
        <div>{brief?.reply || "Briefing load ho rahi hai…"}</div>
        <div className="actions">
          <button className="btn" onClick={playBriefing} disabled={!brief}>▶ Sunao</button>
          <button className="btn ghost" onClick={() => onNav("call")}>📞 Aaj ke calls</button>
        </div>
      </div>

      <div className="card">
        <h3>Bharaut-Score — kise udhaar dena chahiye</h3>
        {scores.length === 0 && <div className="empty">Data load ho raha hai…</div>}
        {scores.map((s) => (
          <div key={s.customer}>
            <div className="score-row" onClick={() => setOpen(open === s.customer ? null : s.customer)}>
              <div className="ring" style={{ "--p": s.score, "--ring-c": RING_COLORS[s.band] || "var(--green)" }}>
                <i>{s.score}</i>
              </div>
              <div className="info">
                <b>{s.customer}</b>
                <span>{s.band} · baki {fmt(s.balance)}</span>
              </div>
              <div style={{ color: "var(--muted)", fontSize: 12 }}>{open === s.customer ? "▲" : "▼"}</div>
            </div>
            {open === s.customer && (
              <div className="breakdown">
                <div><b style={{ color: "var(--ink)" }}>Kyun {s.score}?</b> {s.one_liner}</div>
                <div>✅ Wade poore: {s.breakdown.promises_kept}</div>
                <div>❌ Wade tode: {s.breakdown.promises_broken}</div>
                <div>⏳ Pending wade: {s.breakdown.promises_pending}
                  {s.breakdown.promises_overdue > 0 && <> (⚠️ {s.breakdown.promises_overdue} overdue)</>}
                </div>
                <div>🐢 Der se payments: {s.breakdown.late_payments}</div>
                {s.breakdown.adjustments.length > 0 && (
                  <div>🧮 {s.breakdown.adjustments.join(" · ")}</div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card" style={{ fontSize: 12.5, color: "var(--muted)" }}>
        Trust Score ek explainable formula hai: wada toda −25 · der se payment −10 ·
        30+ din purana baki −5 · har poora wada +5 (max +20). Koi black box nahi —
        dukaandaar ko poora hisaab dikhta hai.
      </div>
    </>
  );
}
