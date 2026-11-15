import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { fmt, fmtDate, whatsappLink } from "../util.js";
import { Icon } from "../icons.jsx";

const PROMISE_LABEL = { PENDING: "⏳ Pending", KEPT: "✅ Poora kiya", BROKEN: "❌ Toda" };
const OUTCOME_LABEL = { PROMISE: "Wada mila", PARTIAL: "Thoda mila + wada", REFUSED: "Wada nahi", IN_PROGRESS: "Adhoori" };

// One customer's whole khata: balance, entries (with delete), promises, calls.
export default function CustomerDetail({ cid, me, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [armed, setArmed] = useState(null);   // entry id waiting for the second "pakka?" tap

  const load = () => api.ledger(cid).then(setData).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [cid]);

  const remove = async (id) => {
    if (armed !== id) { setArmed(id); return; }
    setArmed(null);
    try {
      await api.deleteEntry(id);
      await load();
      onChanged && onChanged();
    } catch (e) { setErr("Entry nahi hati: " + e.message); }
  };

  const pending = data?.promises.find((p) => p.status === "PENDING");

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <div>
            <h2>{data?.customer.name || "…"}</h2>
            <small>Bakipada <b style={{ color: "var(--red)" }}>{data ? fmt(data.balance) : "—"}</b></small>
          </div>
          <button className="sheet-close" onClick={onClose} aria-label="Band karo">✕</button>
        </div>

        {err && <div className="auth-err">{err}</div>}
        {!data && !err && <div className="empty">Khata khul raha hai…</div>}

        {data && (
          <>
            {data.balance > 0 && (
              <a className="btn wa" target="_blank" rel="noreferrer"
                 href={whatsappLink({ name: data.customer.name, shop: me?.shop_name || me?.name,
                                      balance: data.balance, promise: pending })}>
                💬 WhatsApp pe yaad dilao
              </a>
            )}

            <h3>Wade</h3>
            {data.promises.length === 0 && <div className="empty">Abhi koi wada nahi.</div>}
            {data.promises.map((p) => (
              <div key={p.id} className="prov">
                <span>{fmt(p.amount)} · {fmtDate(p.due_date)} tak</span>
                <span className={"pill st-" + p.status.toLowerCase()}>{PROMISE_LABEL[p.status] || p.status}</span>
              </div>
            ))}

            <h3>Entries</h3>
            {data.entries.length === 0 && <div className="empty">Koi entry nahi.</div>}
            {data.entries.map((e) => (
              <div key={e.id} className={"entry " + (e.type === "UDHAAR" ? "udhaar" : "payment")}>
                <div className="tag"><Icon name={e.type === "UDHAAR" ? "up" : "down"} size={19} stroke={2.2} /></div>
                <div className="meta">
                  <b>{e.type === "UDHAAR" ? "Udhaar" : "Payment"} · {fmtDate(e.created_at, { relative: false })}</b>
                  <span>{e.raw_transcript || e.items_text || "—"}</span>
                </div>
                <div className="amt">{e.type === "UDHAAR" ? "+" : "−"}{fmt(e.amount)}</div>
                <button className={"del" + (armed === e.id ? " armed" : "")} onClick={() => remove(e.id)}
                        title="Galat entry hatao">
                  {armed === e.id ? "Pakka?" : "🗑"}
                </button>
              </div>
            ))}

            <h3>Calls</h3>
            {data.calls.length === 0 && <div className="empty">Abhi koi call nahi hui.</div>}
            {data.calls.map((c) => (
              <div key={c.id} className="callrow">
                <b>{fmtDate(c.started_at, { relative: false })} · {OUTCOME_LABEL[c.outcome] || c.outcome}</b>
                <span>{c.summary || "—"}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
