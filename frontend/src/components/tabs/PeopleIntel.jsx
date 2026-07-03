import React, { useState } from "react";
import api from "../../lib/api";
import { UserSearch, AlertTriangle } from "lucide-react";

export function PeopleIntel() {
  const [form, setForm] = useState({ name: "", email: "", phone: "", username: "", model: "deepseek" });
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const upd = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const scan = async () => {
    setBusy(true); setReport(null);
    try { const r = await api.post("/people-intel/scan", form); setReport(r.data); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  const riskColor = { low: "var(--accent)", medium: "var(--amber)", high: "var(--danger)" };

  return (
    <div className="fade-in">
      <div className="section-title">People Intelligence · OSINT Resolver</div>
      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 16 }}>
        <div className="panel">
          <div className="panel-head"><h3>Subject Inputs</h3></div>
          <div className="panel-body">
            {["name", "username", "email", "phone"].map((k) => (
              <div className="field" key={k}>
                <label>{k}</label>
                <input className="input" value={form[k]} onChange={(e) => upd(k, e.target.value)}
                  placeholder={k === "username" ? "e.g. torvalds" : k} data-testid={`pi-${k}`} />
              </div>
            ))}
            <div className="field">
              <label>AI Model</label>
              <select className="select" style={{ width: "100%" }} value={form.model} onChange={(e) => upd("model", e.target.value)} data-testid="pi-model">
                <option value="deepseek">DeepSeek V3.1</option>
                <option value="qwen">Qwen 2.5 32B</option>
              </select>
            </div>
            <button className="btn" onClick={scan} disabled={busy} data-testid="pi-scan">
              {busy ? <span className="spinner" /> : <><UserSearch size={15} /> Run Scan</>}
            </button>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>Intelligence Report</h3>
            {report && <span className="badge" style={{ color: riskColor[report.risk.level], borderColor: riskColor[report.risk.level] }}>
              <AlertTriangle size={11} style={{ verticalAlign: -1, marginRight: 5 }} />RISK: {report.risk.level.toUpperCase()}</span>}
          </div>
          <div className="panel-body" data-testid="pi-report">
            {!report ? <div className="empty"><UserSearch size={36} /><div>Enter identifiers and run a scan.</div></div>
            : (
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6 }}>AI PROFILE · {(report.ai_profile.confidence * 100).toFixed(0)}% conf</div>
                  <div style={{ fontSize: 14, lineHeight: 1.6 }}>{report.ai_profile.summary}</div>
                  <div className="mono" style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
                    {report.ai_profile.occupation_guess} · {report.ai_profile.personality}
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                    {(report.ai_profile.interests || []).map((t) => <span key={t} className="badge cold">{t}</span>)}
                  </div>
                </div>
                <div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>DIGITAL FOOTPRINT ({report.footprint.accounts.length})</div>
                  {report.footprint.accounts.length ? report.footprint.accounts.map((a) => (
                    <a key={a.platform + a.url} href={a.url} target="_blank" rel="noreferrer" className="key-row" style={{ marginBottom: 8, display: "flex" }}>
                      <div className="kmeta"><b>{a.platform}</b><div className="pfx">{a.url}</div></div>
                      <span className="badge hot">{(a.confidence * 100).toFixed(0)}%</span>
                    </a>
                  )) : <div className="muted mono" style={{ fontSize: 12 }}>No public accounts detected.</div>}
                </div>
                <div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>PUBLIC RECORDS ({report.public_records.records.length})</div>
                  {report.public_records.records.map((r) => (
                    <div key={r.category + r.source + r.description} style={{ fontSize: 13, padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                      <span className="badge">{r.category}</span> <span className="muted">{r.description}</span>
                    </div>
                  ))}
                </div>
                {report.risk.reasons.length > 0 && (
                  <div>
                    <div className="mono" style={{ fontSize: 11, color: "var(--danger)", marginBottom: 8 }}>RISK INDICATORS</div>
                    {report.risk.reasons.map((r) => <div key={r} style={{ fontSize: 13, color: "var(--amber)" }}>⚠ {r}</div>)}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
