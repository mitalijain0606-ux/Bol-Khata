// Tiny API layer — everything talks to the FastAPI backend.
const j = async (r) => {
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.status === 204 ? null : r.json();
};

export const api = {
  health: () => fetch("/api/health").then(j),
  shopkeeper: () => fetch("/api/shopkeeper").then(j),

  customers: () => fetch("/api/customers").then(j),
  ledger: (cid) => fetch(`/api/customers/${cid}/ledger`).then(j),
  addCustomer: (name, persona = "", phone = "") =>
    fetch("/api/customers", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, persona, phone }),
    }).then(j),

  entries: (limit = 30) => fetch(`/api/entries?limit=${limit}`).then(j),
  totals: () => fetch("/api/totals").then(j),
  trustScores: () => fetch("/api/trust-scores").then(j),
  briefing: () => fetch("/api/briefing").then(j),

  // rule-engine brain (works offline/mock) and full brain (Evon when configured)
  command: (text, lang = "hi-IN") =>
    fetch("/api/voice/command", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang }),
    }).then(j),

  tts: (text, voice = "", lang = "hi-IN") =>
    fetch(`/api/tts?text=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}&lang=${lang}`),

  // collections call simulator
  callStart: (cid) => fetch(`/api/call/start/${cid}`, { method: "POST" }).then(j),
  callStep: (id) => fetch(`/api/call/${id}/step`, { method: "POST" }).then(j),
  callSay: (id, text) =>
    fetch(`/api/call/${id}/say`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }).then(j),
  callEnd: (id) => fetch(`/api/call/${id}/end`, { method: "POST" }).then(j),

  enroll: (sid, blob) => {
    const fd = new FormData();
    fd.append("file", blob, "enroll.wav");
    return fetch(`/api/shopkeeper/${sid}/enroll`, { method: "POST", body: fd }).then(j);
  },
};
