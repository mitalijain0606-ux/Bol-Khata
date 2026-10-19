// Tiny API layer — attaches the session token to every call.
const TOKEN_KEY = "bolkhata_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

const j = async (r) => {
  if (r.status === 401) {
    clearToken();
    window.location.reload(); // session expired -> back to login
    throw new Error("logged out");
  }
  if (!r.ok) {
    let detail = `${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return r.status === 204 ? null : r.json();
};

const authHeaders = () => {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
};
const post = (url, body) =>
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  }).then(j);
const get = (url) => fetch(url, { headers: authHeaders() }).then(j);

export const api = {
  // ---- auth ----
  login: (phone, password) => post("/api/auth/login", { phone, password }),
  register: (name, shop_name, phone, password) =>
    post("/api/auth/register", { name, shop_name, phone, password }),
  me: () => get("/api/auth/me"),

  health: () => get("/api/health"),
  shopkeeper: () => get("/api/shopkeeper"),

  customers: () => get("/api/customers"),
  ledger: (cid) => get(`/api/customers/${cid}/ledger`),

  entries: (limit = 30) => get(`/api/entries?limit=${limit}`),
  totals: () => get("/api/totals"),
  trustScores: () => get("/api/trust-scores"),
  briefing: () => get("/api/briefing"),

  // rule-engine brain (free) — Evon upgrades server-side
  command: (text, lang = "hi-IN") => post("/api/voice/command", { text, lang }),

  tts: (text, voice = "", lang = "hi-IN") =>
    fetch(`/api/tts?text=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}&lang=${lang}`),

  // collections call simulator
  callStart: (cid) => fetch(`/api/call/start/${cid}`, { method: "POST", headers: authHeaders() }).then(j),
  callStep: (id) => fetch(`/api/call/${id}/step`, { method: "POST", headers: authHeaders() }).then(j),
  callSay: (id, text) => post(`/api/call/${id}/say`, { text }),
  callEnd: (id) => fetch(`/api/call/${id}/end`, { method: "POST", headers: authHeaders() }).then(j),

  enroll: (sid, blob) => {
    const fd = new FormData();
    fd.append("file", blob, "enroll.wav");
    return fetch(`/api/shopkeeper/${sid}/enroll`, { method: "POST", body: fd }).then(j);
  },
};
