import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { KeyRound, Copy, Plus, Trash2 } from "lucide-react";

export function ApiKeys() {
  const [keys, setKeys] = useState([]);
  const [revealed, setRevealed] = useState(null);
  const [name, setName] = useState("");
  const load = () => api.get("/keys").then((r) => setKeys(r.data));
  useEffect(() => { load(); }, []);

  const gen = async () => {
    const { data } = await api.post("/keys", { name: name || "default" });
    setRevealed(data); setName(""); load();
  };
  const revoke = async (id) => { if (window.confirm("Revoke this key?")) { await api.delete(`/keys/${id}`); load(); } };

  return (
    <div className="fade-in">
      <div className="section-title">API Keys · Machine Access</div>
      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-head"><h3>Generate Key</h3></div>
        <div className="panel-body">
          {revealed && (
            <div className="key-reveal" data-testid="key-reveal">
              <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>NEW KEY — “{revealed.name}”</div>
              <code className="code">{revealed.api_key}</code>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <button className="btn btn-ghost btn-sm" onClick={() => navigator.clipboard.writeText(revealed.api_key)}><Copy size={13} /> Copy</button>
                <span className="warn">⚠ {revealed.warning}</span>
              </div>
            </div>
          )}
          <div className="toolbar">
            <input className="search-input" style={{ flex: 1 }} placeholder="Key label (e.g. production)"
              value={name} onChange={(e) => setName(e.target.value)} data-testid="key-name-input" />
            <button className="btn btn-sm" onClick={gen} data-testid="key-generate"><Plus size={14} /> Generate</button>
          </div>
          <p className="mono" style={{ fontSize: 11, color: "var(--muted)", marginTop: 14 }}>
            Authenticate requests with header <span style={{ color: "var(--accent)" }}>X-API-Key: nxs_…</span>
          </p>
        </div>
      </div>

      <div className="section-title">Active Keys</div>
      {keys.map((k) => (
        <div className="key-row" key={k.id} data-testid={`key-row-${k.id}`}>
          <div className="kmeta">
            <b><KeyRound size={14} style={{ verticalAlign: -2, marginRight: 8, color: "var(--accent)" }} />{k.name}</b>
            <div className="pfx">{k.prefix}••••••••••••{k.revoked && <span style={{ color: "var(--danger)" }}> (revoked)</span>}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div className="kstats">{k.calls} calls · last {k.last_used ? new Date(k.last_used).toLocaleDateString() : "never"}</div>
            {!k.revoked && <button className="icon-btn danger" onClick={() => revoke(k.id)} data-testid={`key-revoke-${k.id}`}><Trash2 size={14} /></button>}
          </div>
        </div>
      ))}
      {!keys.length && <div className="empty"><KeyRound size={36} /><div>No API keys yet.</div></div>}
    </div>
  );
}
