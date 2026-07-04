import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { ShieldAlert, Copy, Send } from "lucide-react";

const riskColor = (s) => {
  if (s > 7) return "var(--danger)";
  if (s > 5) return "var(--amber)";
  return "var(--accent)";
};
const severityClass = (sev) => {
  if (sev === "high") return "hot";
  if (sev === "medium") return "warm";
  return "cold";
};

function ThreatProfileEditor({ profile, setProfile, onSave }) {
  return (
    <div className="panel" style={{ marginBottom: 18 }}>
      <div className="panel-head"><h3>Your Sales Identity (used in AI pitches)</h3></div>
      <div className="panel-body">
        <div className="toolbar" style={{ flexWrap: "wrap", gap: 10 }}>
          {[["sender_name", "Your name"], ["sender_email", "From email"], ["brand", "Company/brand"], ["cta", "Booking/CTA link"]].map(([k, ph]) => (
            <input key={k} className="search-input" placeholder={ph} value={profile[k] || ""}
              onChange={(e) => setProfile((p) => ({ ...p, [k]: e.target.value }))} data-testid={`threat-prof-${k}`} />
          ))}
          <input className="search-input" style={{ flex: 1, minWidth: 280 }} placeholder="services you sell (e.g. pentesting, breach remediation, vCISO)"
            value={profile.services || ""} onChange={(e) => setProfile((p) => ({ ...p, services: e.target.value }))} data-testid="threat-prof-services" />
          <button className="btn btn-sm" onClick={onSave} data-testid="threat-prof-save">Save</button>
        </div>
      </div>
    </div>
  );
}

function ThreatDnsPanel({ report }) {
  return (
    <div data-testid="threat-dns-panel" style={{ marginTop: 16, padding: 12, border: "1px solid var(--line)", fontSize: 12.5 }}>
      <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>DNS & INFRASTRUCTURE</div>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 14px" }}>
        <span className="muted">DNSSEC</span><span><span className={`badge ${report.dnssec_enabled ? "cold" : "warm"}`}>{report.dnssec_enabled ? "enabled" : "disabled"}</span></span>
        <span className="muted">IP</span><span className="mono">{report.ip || "—"}</span>
        {report.dns?.A?.length > 0 && (<><span className="muted">A</span><span className="mono">{report.dns.A.join(", ")}</span></>)}
        {report.dns?.NS?.length > 0 && (<><span className="muted">NS</span><span className="mono">{report.dns.NS.join(", ")}</span></>)}
        {report.dns?.MX?.length > 0 && (<><span className="muted">MX</span><span className="mono">{report.dns.MX.join(", ")}</span></>)}
        {report.shodan?.org && (<><span className="muted">Host org</span><span>{report.shodan.org}</span></>)}
        {report.shodan?.ports?.length > 0 && (<><span className="muted">Open ports</span><span className="mono">{report.shodan.ports.join(", ")}</span></>)}
        {report.shodan?.vulns?.length > 0 && (<><span className="muted">Known CVEs</span><span className="mono" style={{ color: "var(--hot, #e5484d)" }}>{report.shodan.vulns.slice(0, 6).join(", ")}{report.shodan.vulns.length > 6 ? "…" : ""}</span></>)}
        {report.ssl?.valid && (<><span className="muted">TLS cert</span><span>{report.ssl.issuer || "valid"} · {report.ssl.protocol}{report.ssl.days_to_expiry != null ? ` · expires in ${report.ssl.days_to_expiry}d` : ""}</span></>)}
        {report.ssl && report.ssl.available && !report.ssl.valid && (<><span className="muted">TLS cert</span><span style={{ color: "var(--hot, #e5484d)" }}>invalid/untrusted</span></>)}
        {report.ssl && report.ssl.available === false && (<><span className="muted">TLS cert</span><span style={{ color: "var(--hot, #e5484d)" }}>no HTTPS on :443</span></>)}
      </div>
    </div>
  );
}

function ThreatReportCard({ report }) {
  return (
    <div data-testid="threat-report" style={{ marginTop: 20, display: "grid", gridTemplateColumns: "200px 1fr", gap: 20 }}>
      <div style={{ textAlign: "center", padding: 20, border: "1px solid var(--line)" }}>
        <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>RISK SCORE</div>
        <div style={{ fontFamily: "var(--head)", fontSize: 56, fontWeight: 700, color: riskColor(report.risk_score) }}>{report.risk_score}</div>
        <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>/ 10</div>
        <span className="badge" style={{ marginTop: 10, color: riskColor(report.risk_score), borderColor: riskColor(report.risk_score) }}>{report.risk_level}</span>
        {report.high_ticket && <div className="badge sold" style={{ marginTop: 10 }}>HIGH-TICKET</div>}
      </div>
      <div>
        <div style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 14 }}>{report.executive_summary}</div>
        <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>FINDINGS ({report.findings.length})</div>
        {report.findings.map((f) => (
          <div key={f.category + f.detail} style={{ fontSize: 13, padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
            <span className={`badge ${severityClass(f.severity)}`}>{f.severity}</span>{" "}
            <span className="muted">{f.detail}</span>
          </div>
        ))}
        {(report.dns || report.shodan) && <ThreatDnsPanel report={report} />}
      </div>
    </div>
  );
}

function ThreatEmailDraft({ report, sendTo, setSendTo, sending, onSend }) {
  return (
    <div className="key-reveal" style={{ marginTop: 20 }} data-testid="threat-email-draft">
      <div className="mono" style={{ fontSize: 11, color: "var(--accent)" }}>📧 AI SALES PITCH (DRAFT) → {report.domain}</div>
      <div style={{ fontWeight: 600, margin: "10px 0 6px" }}>Subject: {report.email_draft.subject}</div>
      <div style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.6 }}>{report.email_draft.body}</div>
      <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }}
        onClick={() => navigator.clipboard.writeText(`Subject: ${report.email_draft.subject}\n\n${report.email_draft.body}`)} data-testid="threat-email-copy">
        <Copy size={13} /> Copy email
      </button>
      <div className="toolbar" style={{ marginTop: 12, gap: 8 }}>
        <input className="search-input" placeholder="recipient email (e.g. it@company.com)" value={sendTo}
          onChange={(e) => setSendTo(e.target.value)} data-testid="threat-send-to" />
        <button className="btn btn-sm" onClick={onSend} disabled={sending || !sendTo.trim()} data-testid="threat-send-email">
          {sending ? <span className="spinner" /> : <><Send size={13} /> Send via Gmail</>}
        </button>
      </div>
    </div>
  );
}

function ThreatTargetsTable({ reports }) {
  return (
    <div className="panel">
      <div className="panel-body" style={{ padding: 0 }}>
        <table className="tbl">
          <thead><tr><th>Domain</th><th>Risk</th><th>Level</th><th>Vulnerabilities</th><th>Pitch</th><th>Scanned</th></tr></thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.id} data-testid={`threat-row-${r.id}`}>
                <td className="name">{r.domain}{r.high_ticket && <span className="badge sold" style={{ marginLeft: 8 }}>HOT</span>}</td>
                <td><span className="badge" style={{ color: riskColor(r.risk_score), borderColor: riskColor(r.risk_score) }}>{r.risk_score}</span></td>
                <td className="muted">{r.risk_level}</td>
                <td className="muted" style={{ fontSize: 12, maxWidth: 280 }}>{(r.top_vulnerabilities || []).join(", ") || `${r.findings?.length || 0} findings`}</td>
                <td>{r.email_draft ? <span className="badge hot">drafted</span> : <span className="muted">—</span>}</td>
                <td className="muted">{r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}</td>
              </tr>
            ))}
            {!reports.length && <tr><td colSpan={6} className="empty">No scans yet — scan a company above.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ThreatIntel() {
  const [domain, setDomain] = useState("");
  const [model, setModel] = useState("deepseek");
  const [report, setReport] = useState(null);
  const [reports, setReports] = useState([]);
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState(null);
  const [showProfile, setShowProfile] = useState(false);
  const [sendTo, setSendTo] = useState("");
  const [sending, setSending] = useState(false);

  const loadReports = () => api.get("/threat/reports?limit=30").then((r) => setReports(r.data)).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only initial load
  useEffect(() => {
    loadReports();
    api.get("/threat/outreach-profile").then((r) => setProfile({ sender_name: "", sender_email: "", brand: "", services: "", cta: "", ...r.data })).catch(() => {});
  }, []);

  const scan = async () => {
    if (!domain.trim()) return;
    setBusy(true); setReport(null);
    try { const r = await api.post("/threat/scan", { domain: domain.trim(), model }); setReport(r.data); loadReports(); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  const saveProfile = async () => { await api.put("/threat/outreach-profile", profile); setShowProfile(false); };
  const sendPitch = async () => {
    if (!report?.id || !sendTo.trim()) return;
    setSending(true);
    try { await api.post(`/threat/reports/${report.id}/send-email`, { to_email: sendTo.trim() }); alert("Pitch sent to " + sendTo); setSendTo(""); loadReports(); }
    catch (e) { alert(e.response?.data?.detail || e.message); }
    finally { setSending(false); }
  };

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span>Threat Intel · High-Ticket Prospecting</span>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowProfile((s) => !s)} data-testid="threat-profile-toggle">Outreach Profile</button>
      </div>

      {showProfile && profile && <ThreatProfileEditor profile={profile} setProfile={setProfile} onSave={saveProfile} />}

      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="panel-head"><h3>Scan a Company</h3>
          <select className="select" value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="deepseek">DeepSeek</option><option value="qwen">Qwen</option>
          </select>
        </div>
        <div className="panel-body">
          <div className="toolbar">
            <input className="search-input" style={{ flex: 1 }} placeholder="company domain e.g. acme.com" value={domain}
              onChange={(e) => setDomain(e.target.value)} onKeyDown={(e) => e.key === "Enter" && scan()} data-testid="threat-domain" />
            <button className="btn btn-sm" onClick={scan} disabled={busy} data-testid="threat-scan">
              {busy ? <span className="spinner" /> : <><ShieldAlert size={14} /> Scan & Score</>}
            </button>
          </div>

          {report && <ThreatReportCard report={report} />}

          {report?.email_draft && (
            <ThreatEmailDraft report={report} sendTo={sendTo} setSendTo={setSendTo} sending={sending} onSend={sendPitch} />
          )}
        </div>
      </div>

      <div className="section-title">High-Ticket Targets ({reports.filter((r) => r.high_ticket).length})</div>
      <ThreatTargetsTable reports={reports} />
    </div>
  );
}
