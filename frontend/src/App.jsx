import React, { useEffect, useState } from "react";
import { api, getToken, clearToken } from "./api.js";
import { speechSupported } from "./voice.js";
import Auth from "./pages/Auth.jsx";
import Khata from "./pages/Khata.jsx";
import CallScreen from "./pages/CallScreen.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Settings from "./pages/Settings.jsx";

const TABS = [
  { key: "khata", ic: "🎤", label: "Khata" },
  { key: "call", ic: "📞", label: "Calls" },
  { key: "dash", ic: "📊", label: "Hisaab" },
  { key: "set", ic: "⚙️", label: "Setting" },
];

export default function App() {
  const [authed, setAuthed] = useState(null); // null=checking, false=login, obj=shopkeeper
  const [tab, setTab] = useState("khata");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ providers: {} }));
    if (getToken()) {
      api.me().then(setAuthed).catch(() => setAuthed(false));
    } else {
      setAuthed(false);
    }
  }, []);

  const refreshMe = () => api.me().then(setAuthed).catch(() => {});

  const logout = () => {
    clearToken();
    window.location.reload();
  };

  if (authed === null) {
    return <div className="auth-wrap"><div className="auth-hero"><div className="logo-big">ब</div><h1>Bol-Khata</h1></div></div>;
  }
  if (authed === false) {
    return <Auth onLogin={refreshMe} />;
  }

  const live = health?.providers?.stt;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="logo">ब</div>
          <div>
            <h1>Bol-Khata</h1>
            <small>{authed.shop_name || authed.name}</small>
          </div>
        </div>
        <div className="live-chip">
          <span className="dot" /> {live ? "AI Live" : "AI Ready"}
        </div>
      </header>

      <main className="page">
        {tab === "khata" && <Khata gnani={live} onNav={setTab} />}
        {tab === "call" && <CallScreen />}
        {tab === "dash" && <Dashboard onNav={setTab} />}
        {tab === "set" && <Settings me={authed} onSaved={refreshMe} onLogout={logout} />}
      </main>

      <nav className="navbar">
        {TABS.map((t) => (
          <button key={t.key} className={tab === t.key ? "active" : ""} onClick={() => setTab(t.key)}>
            <span className="ic">{t.ic}</span>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}

export { speechSupported };
