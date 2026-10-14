import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { speechSupported } from "./voice.js";
import Khata from "./pages/Khata.jsx";
import CallScreen from "./pages/CallScreen.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Settings from "./pages/Settings.jsx";

const TABS = [
  { key: "khata", ic: "🎤", label: "Khata" },
  { key: "call", ic: "📞", label: "Calls" },
  { key: "dash", ic: "📊", label: "Hisaab" },
  { key: "set", ic: "⚙️", label: "Settings" },
];

export default function App() {
  const [tab, setTab] = useState("khata");
  const [health, setHealth] = useState(null);
  const [shop, setShop] = useState(null);

  const refresh = () => {
    api.health().then(setHealth).catch(() => setHealth({ mode: "offline", providers: {} }));
    api.shopkeeper().then(setShop).catch(() => {});
  };
  useEffect(refresh, []);

  const gnani = health?.mode === "gnani";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="logo">ब</div>
          <div>
            <h1>Bol-Khata</h1>
            <small>{shop ? `${shop.shop_name} · ${shop.name}` : "bolke khata, bolke vasooli"}</small>
          </div>
        </div>
        <div className={"mode-chip" + (gnani ? " gnani" : "")}>
          {gnani ? <>Gnani <b>Prisma·Timbre·Evon</b></> : <>Mode: <b>Mock (free)</b></>}
        </div>
      </header>

      <main className="page">
        {tab === "khata" && <Khata gnani={gnani} onNav={setTab} />}
        {tab === "call" && <CallScreen gnani={gnani} />}
        {tab === "dash" && <Dashboard onNav={setTab} />}
        {tab === "set" && <Settings health={health} shop={shop} onSaved={refresh} />}
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
