import React, { useState } from "react";
import { api, setToken } from "../api.js";

export default function Auth({ onLogin }) {
  const [mode, setMode] = useState("login"); // login | register
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [shopName, setShopName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const res = mode === "login"
        ? await api.login(phone, password)
        : await api.register(name, shopName, phone, password);
      setToken(res.token);
      onLogin(res.shopkeeper);
    } catch (e2) {
      setErr(e2.message || "Kuch gadbad ho gayi — dobara koshish karein");
    }
    setBusy(false);
  };

  const fillDemo = () => {
    setMode("login");
    setPhone("9876543210");
    setPassword("demo1234");
  };

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <div className="logo-big">ब</div>
        <h1>Bol-Khata</h1>
        <p>Aapki dukaan ka AI manager — bolke khata, bolke vasooli</p>
      </div>

      <div className="auth-card">
        <div className="auth-toggle">
          <button className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setErr(""); }}>
            Login
          </button>
          <button className={mode === "register" ? "active" : ""} onClick={() => { setMode("register"); setErr(""); }}>
            Naya account
          </button>
        </div>

        {err && <div className="auth-err">{err}</div>}

        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <div className="field">
                <label>Aapka naam</label>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ramesh Kumar" required />
              </div>
              <div className="field">
                <label>Dukaan ka naam</label>
                <input value={shopName} onChange={(e) => setShopName(e.target.value)} placeholder="Sharma Kirana Store" />
              </div>
            </>
          )}
          <div className="field">
            <label>Mobile number</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)}
                   placeholder="9876543210" inputMode="numeric" required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                   placeholder="••••••" required />
          </div>
          <button className="btn" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Ruko…" : mode === "login" ? "Khata kholo" : "Account banao"}
          </button>
        </form>

        {mode === "login" && (
          <div className="auth-hint">
            Demo account try karna hai? <b onClick={fillDemo}>Yahan tap karo</b>
            <br />(9876543210 · demo1234)
          </div>
        )}
      </div>
    </div>
  );
}
