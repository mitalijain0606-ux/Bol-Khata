import React, { useEffect, useState } from "react";
import { api, getToken, clearToken } from "./api.js";
import { speechSupported } from "./voice.js";
import Logo from "./Logo.jsx";
import { Icon } from "./icons.jsx";
import Auth from "./pages/Auth.jsx";
import Khata from "./pages/Khata.jsx";
import CallScreen from "./pages/CallScreen.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Settings from "./pages/Settings.jsx";

const THEME_KEY = "bolkhata_theme_v2";
const applyTheme = (t) => document.body.classList.toggle("light", t === "light");

const TABS = [
  { key: "khata", ic: "mic", label: "Khata" },
  { key: "call", ic: "phone", label: "Calls" },
  { key: "dash", ic: "chart", label: "Hisaab" },
  { key: "set", ic: "gear", label: "Setting" },
];

export default function App() {
  const [authed, setAuthed] = useState(null); // null=checking, false=login, obj=shopkeeper
  const [tab, setTab] = useState("khata");
  const [health, setHealth] = useState(null);
  const [theme, setTheme] = useState(localStorage.getItem(THEME_KEY) || "light");

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ providers: {} }));
    if (getToken()) {
      api.me().then(setAuthed).catch(() => setAuthed(false));
    } else {
      setAuthed(false);
    }
  }, []);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  const refreshMe = () => api.me().then(setAuthed).catch(() => {});

  const logout = () => {
    clearToken();
    window.location.reload();
  };

  if (authed === null) {
    return (
      <div className="auth-wrap">
        <div className="auth-hero">
          <Logo size={74} radius={24} />
          <h1>Bol-Khata</h1>
        </div>
      </div>
    );
  }
  if (authed === false) {
    return (
      <>
        <button className="theme-fab" onClick={toggleTheme} title="Theme badlo">
          <Icon name={theme === "dark" ? "sun" : "moon"} size={18} />
        </button>
        <Auth onLogin={refreshMe} />
      </>
    );
  }

  const live = health?.providers?.stt;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <Logo size={42} />
          <div>
            <h1>Bol-Khata</h1>
            <small>{authed.shop_name || authed.name}</small>
          </div>
        </div>
        <button className="theme-fab" onClick={toggleTheme} title="Theme badlo">
          <Icon name={theme === "dark" ? "sun" : "moon"} size={17} />
        </button>
      </header>

      <main className="page" key={tab}>
        {tab === "khata" && <Khata gnani={live} onNav={setTab} me={authed} />}
        {tab === "call" && <CallScreen me={authed} onNav={setTab} />}
        {tab === "dash" && <Dashboard onNav={setTab} me={authed} />}
        {tab === "set" && <Settings me={authed} onSaved={refreshMe} onLogout={logout} />}
      </main>

      <nav className="navbar">
        {TABS.map((t) => (
          <button key={t.key} className={tab === t.key ? "active" : ""} onClick={() => setTab(t.key)}>
            <span className="ic"><Icon name={t.ic} size={21} /></span>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}

export { speechSupported };
