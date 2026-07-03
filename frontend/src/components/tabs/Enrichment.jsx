import React, { useState } from "react";
import api from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { CreditCard, Boxes } from "lucide-react";

const ENRICH_COST = { business: 1, person: 1, property: 1, osint: 1, lead: 3 };
const ENRICH_TYPES = [
  { id: "business", label: "Business", fields: ["name", "domain", "phone", "address"] },
  { id: "person", label: "Person", fields: ["name", "email", "phone", "username"] },
  { id: "property", label: "Property", fields: ["address"] },
  { id: "osint", label: "OSINT", fields: ["target"] },
  { id: "lead", label: "Lead (composite)", fields: ["name", "domain", "target"] },
];

export function Enrichment() {
  const { user, refreshUser } = useAuth();
  const [type, setType] = useState("business");
  const [form, setForm] = useState({});
  const [model, setModel] = useState("deepseek");
  const [out, setOut] = useState(null);
  const [busy, setBusy] = useState(false);
  const cfg = ENRICH_TYPES.find((t) => t.id === type);
  const upd = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const run = async () => {
    setBusy(true); setOut(null);
    try {
      let url; let body;
      if (type === "lead") {
        url = "/enrich/lead";
        body = {
          model,
          business: form.name ? { name: form.name, domain: form.domain || "", model } : undefined,
          osint: form.target ? { target: form.target, model } : undefined,
        };
      } else {
        url = `/enrich/${type}`;
        body = { ...form, model };
      }
      const r = await api.post(url, body);
      setOut(r.data);
      await refreshUser();
    } catch (e) {
      if (e.response?.status === 402) {
        setOut({ error: e.response.data.detail });
        if (window.confirm("Out of credits. Go to Billing to buy a pack?")) window.dispatchEvent(new CustomEvent("nexus-goto", { detail: "billing" }));
      } else setOut({ error: e.response?.data?.detail || e.message });
    } finally { setBusy(false); }
  };

  const switchType = (t) => { setType(t); setForm({}); setOut(null); };

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span>Enrichment Engine · Paid API</span>
        <span className="mono" style={{ fontSize: 12, color: "var(--accent)" }}>
          <CreditCard size={13} style={{ verticalAlign: -2, marginRight: 6 }} />{user?.credits ?? 0} credits
        </span>
      </div>
      <div className="osint-grid" style={{ marginBottom: 20 }}>
        {ENRICH_TYPES.map((t) => (
          <div key={t.id} className={`tool-card ${type === t.id ? "active" : ""}`}
            onClick={() => switchType(t.id)} data-testid={`enrich-type-${t.id}`}>
            <div className="ico"><Boxes size={18} /></div>
            <h4>{t.label}</h4>
            <p>POST /api/enrich/{t.id}</p>
            <span className="badge hot" style={{ marginTop: 8 }}>{ENRICH_COST[t.id]} credit{ENRICH_COST[t.id] > 1 ? "s" : ""}</span>
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="panel-head"><h3>{cfg.label} Enrichment · {ENRICH_COST[type]} credit{ENRICH_COST[type] > 1 ? "s" : ""}/call</h3>
          <select className="select" value={model} onChange={(e) => setModel(e.target.value)} data-testid="enrich-model">
            <option value="deepseek">DeepSeek</option>
            <option value="qwen">Qwen</option>
          </select>
        </div>
        <div className="panel-body">
          <div className="toolbar" style={{ marginBottom: 16, flexWrap: "wrap" }}>
            {cfg.fields.map((f) => (
              <input key={f} className="search-input" placeholder={f} value={form[f] || ""}
                onChange={(e) => upd(f, e.target.value)} data-testid={`enrich-field-${f}`} />
            ))}
            <button className="btn btn-sm" onClick={run} disabled={busy} data-testid="enrich-run">
              {busy ? <span className="spinner" /> : <><Boxes size={14} /> Enrich</>}
            </button>
          </div>
          <div className="result-box" data-testid="enrich-result">
            {out ? JSON.stringify(out, null, 2) : <span className="placeholder">// enriched firmographic + identity data renders here as JSON · billed per call</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
