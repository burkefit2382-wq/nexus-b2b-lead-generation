import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { formatApiErrorDetail } from "../lib/api";
import { Radar, ShieldCheck, Crosshair, Network, KeyRound } from "lucide-react";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name || "Operator");
    } catch (ex) {
      setErr(formatApiErrorDetail(ex.response?.data?.detail) || ex.message);
    } finally { setBusy(false); }
  };

  const submitLabel = mode === "login" ? "Authenticate" : "Provision Account";

  return (
    <div className="auth-wrap">
      <div className="auth-left">
        <div>
          <div className="brand-badge">
            <span className="dot" />
            <span className="brand-title">NEXUS</span>
          </div>
          <h1 className="auth-hero-h">OSINT &<br /><span>Lead Intelligence</span><br />Orchestrator</h1>
          <p className="auth-hero-p">
            One command center for digital reconnaissance and AI-scored lead generation.
            Run 12 OSINT tools, enrich leads with DeepSeek, and ship intel via secure API keys.
          </p>
        </div>
        <div className="auth-feats">
          <div className="auth-feat"><Crosshair size={16} /> 12 cloud-native recon tools</div>
          <div className="auth-feat"><Radar size={16} /> AI lead scoring & enrichment</div>
          <div className="auth-feat"><KeyRound size={16} /> Role-based access + API keys</div>
          <div className="auth-feat"><Network size={16} /> Live intel reports & CSV export</div>
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-card fade-in">
          <h2>{mode === "login" ? "Access Terminal" : "Create Operator"}</h2>
          <p className="sub">{mode === "login" ? "Authenticate to enter the command center." : "Provision a new operator account."}</p>
          {err && <div className="err-box" data-testid="auth-error">{err}</div>}
          <form onSubmit={submit}>
            {mode === "register" && (
              <div className="field">
                <label>Callsign / Name</label>
                <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="Operator" data-testid="register-name-input" />
              </div>
            )}
            <div className="field">
              <label>Email</label>
              <input className="input" type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder="agent@nexus.io"
                data-testid="auth-email-input" />
            </div>
            <div className="field">
              <label>Password</label>
              <input className="input" type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
                data-testid="auth-password-input" />
            </div>
            <button className="btn" disabled={busy} type="submit" data-testid="auth-submit-btn">
              {busy ? <span className="spinner" /> : submitLabel}
            </button>
          </form>
          <div className="auth-switch">
            {mode === "login" ? (
              <>No clearance yet? <b onClick={() => { setMode("register"); setErr(""); }} data-testid="switch-register">Create operator</b></>
            ) : (
              <>Already cleared? <b onClick={() => { setMode("login"); setErr(""); }} data-testid="switch-login">Sign in</b></>
            )}
          </div>
          <div className="hint"><ShieldCheck size={12} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            demo: admin@nexus.io / nexus123
          </div>
        </div>
      </div>
    </div>
  );
}
