import React, { useEffect, useState, useRef } from "react";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { cat, scoreClass } from "./helpers";
import {
  Send, Bot, Trash2, RefreshCw, Plus, KeyRound,
  Copy, ShieldAlert, Crosshair, Globe, Network, Smartphone, AtSign,
  MapPin, ScanLine, Server, FileSearch, Search, Users,
  CreditCard, UserSearch, ShieldCheck, AlertTriangle, Boxes,
  Building2, Activity, Database, ScrollText, Inbox, Download, Mail, Zap, Wand2
} from "lucide-react";

/* ============================ OVERVIEW ============================ */
export function Overview({ goTo }) {
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [intel, setIntel] = useState(null);
  useEffect(() => {
    api.get("/leads/stats").then((r) => setStats(r.data)).catch(() => {});
    api.get("/leads?limit=5").then((r) => setLeads(r.data.leads)).catch(() => {});
    api.get("/intel/sources").then((r) => setIntel(r.data)).catch(() => {});
  }, []);
  const S = stats || {};
  const cards = [
    { label: "Total Leads", value: S.total ?? "—", cls: "", sub: `${S.raw ?? 0} raw · ${S.enriched ?? 0} enriched` },
    { label: "Hot Leads", value: S.hot_leads ?? "—", cls: "lime", sub: "score ≥ 70" },
    { label: "Sold", value: S.sold ?? "—", cls: "cyan", sub: "closed deals" },
    { label: "Revenue", value: "$" + (S.total_revenue ?? 0).toLocaleString(), cls: "lime", sub: "lifetime" },
  ];
  return (
    <div className="fade-in">
      <div className="section-title">Operational Overview</div>
      <div className="stat-grid">
        {cards.map((c) => (
          <div className="stat" key={c.label} data-testid={`stat-${c.label.toLowerCase().replace(/ /g,'-')}`}>
            <div className="label">{c.label}</div>
            <div className={`value ${c.cls}`}>{c.value}</div>
            <div className="sub">{c.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 28 }}>
        <div className="panel">
          <div className="panel-head"><h3>Lead Pipeline</h3></div>
          <div className="panel-body">
            {["home_remodeling", "cleaning"].map((k) => {
              const v = k === "home_remodeling" ? S.home_remodeling : S.cleaning;
              const pct = S.total ? Math.round((v / S.total) * 100) : 0;
              return (
                <div key={k} style={{ marginBottom: 18 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span className="mono" style={{ fontSize: 13 }}>{cat(k)}</span>
                    <span className="mono" style={{ fontSize: 13, color: "var(--accent)" }}>{v ?? 0}</span>
                  </div>
                  <div style={{ height: 8, background: "var(--line)" }}>
                    <div style={{ width: `${pct}%`, height: "100%", background: "var(--accent)" }} />
                  </div>
                </div>
              );
            })}
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 8 }} onClick={() => goTo("leads")} data-testid="overview-view-leads">
              View all leads →
            </button>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>Top Scored Leads</h3></div>
          <div className="panel-body" style={{ padding: 0 }}>
            <table className="tbl">
              <tbody>
                {leads.map((l) => (
                  <tr key={l.id}>
                    <td className="name">{l.full_name || l.company || "—"}<div className="muted">{l.city}, {l.state}</div></td>
                    <td><span className={`badge ${scoreClass(l.score)}`}>{Math.round(l.score)}</span></td>
                  </tr>
                ))}
                {!leads.length && <tr><td className="muted" style={{ padding: 22 }}>No leads yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }} data-testid="intel-sources-panel">
        <div className="panel-head"><h3>Intel Sources</h3>
          {intel && <span className="mono" style={{ fontSize: 12, color: "var(--accent)" }}>Apify spend today: ${intel.apify_spend_today_usd?.toFixed(2)} / ${intel.apify_budget_usd?.toFixed(0)}</span>}
        </div>
        <div className="panel-body" style={{ padding: 0 }}>
          <table className="tbl">
            <tbody>
              {(intel?.sources || []).map((s) => (
                <tr key={s.key} data-testid={`intel-source-${s.key}`}>
                  <td className="name">{s.name}<div className="muted">{s.detail}</div></td>
                  <td className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>{s.cost}</td>
                  <td style={{ textAlign: "right" }}>
                    <span className={`badge ${s.status === "live" ? "cold" : "warm"}`}>{s.status === "live" ? "● live" : "○ inactive"}</span>
                  </td>
                </tr>
              ))}
              {!intel && <tr><td className="muted" style={{ padding: 22 }}>Loading sources…</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
/* Leads moved to ./Leads.jsx */

/* ============================ PEOPLE INTELLIGENCE ============================ */
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

/* ============================ BILLING / CREDITS ============================ */
export function Billing() {
  const { user, refreshUser } = useAuth();
  const [pkgs, setPkgs] = useState([]);
  const [busy, setBusy] = useState("");
  const [poll, setPoll] = useState(null);

  useEffect(() => {
    api.get("/payments/packages").then((r) => setPkgs(r.data)).catch(() => {});
    const sid = new URLSearchParams(window.location.search).get("session_id");
    if (sid) startPolling(sid);
    // eslint-disable-next-line
  }, []);

  const startPolling = async (sid, attempt = 0) => {
    setPoll("Verifying payment…");
    if (attempt > 6) { setPoll("Still processing — check back shortly."); return; }
    try {
      const r = await api.get(`/payments/status/${sid}`);
      if (r.data.payment_status === "paid") {
        setPoll(r.data.kind === "lead" ? "✅ Payment complete — lead unlocked! Open the Lead Engine to view full contact." : "✅ Payment complete — credits added!");
        await refreshUser();
        window.history.replaceState({}, "", window.location.pathname);
        return;
      }
      if (r.data.status === "expired") { setPoll("Session expired."); return; }
      setTimeout(() => startPolling(sid, attempt + 1), 2000);
    } catch (e) { setPoll("Could not verify payment."); }
  };

  const buy = async (id) => {
    setBusy(id);
    try {
      const r = await api.post("/payments/checkout", { package_id: id, origin_url: window.location.origin });
      window.location.href = r.data.url;
    } catch (e) { alert(e.response?.data?.detail || e.message); setBusy(""); }
  };

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span>Billing · Lead Credits</span>
        <span className="mono" style={{ fontSize: 13, color: "var(--accent)" }}>
          <CreditCard size={14} style={{ verticalAlign: -2, marginRight: 6 }} />{user?.credits ?? 0} credits available
        </span>
      </div>
      {poll && <div className="key-reveal" data-testid="billing-poll"><span className="mono" style={{ color: "var(--accent)" }}>{poll}</span></div>}
      <div className="osint-grid">
        {pkgs.map((p) => (
          <div className="tool-card" key={p.id} style={{ cursor: "default" }} data-testid={`pkg-${p.id}`}>
            <div className="ico"><CreditCard size={18} /></div>
            <h4>{p.name}</h4>
            <div style={{ fontFamily: "var(--head)", fontSize: 34, fontWeight: 700, margin: "8px 0" }}>${p.amount}</div>
            <p style={{ marginBottom: 14 }}><b style={{ color: "var(--accent)" }}>{p.credits} credits</b> · unlock {p.credits} premium leads</p>
            <button className="btn btn-sm" onClick={() => buy(p.id)} disabled={busy === p.id} data-testid={`buy-${p.id}`}>
              {busy === p.id ? <span className="spinner" /> : "Buy Now"}
            </button>
          </div>
        ))}
      </div>
      <p className="mono" style={{ fontSize: 11, color: "var(--muted)", marginTop: 18 }}>
        1 credit unlocks 1 scraped lead's full contact. Secure checkout via Stripe (test mode). Card: 4242 4242 4242 4242.
      </p>
    </div>
  );
}

/* ============================ THREAT INTEL (owner-only) ============================ */
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
  const riskColor = (s) => (s > 7 ? "var(--danger)" : s > 5 ? "var(--amber)" : "var(--accent)");

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span>Threat Intel · High-Ticket Prospecting</span>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowProfile((s) => !s)} data-testid="threat-profile-toggle">Outreach Profile</button>
      </div>

      {showProfile && profile && (
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
              <button className="btn btn-sm" onClick={saveProfile} data-testid="threat-prof-save">Save</button>
            </div>
          </div>
        </div>
      )}

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

          {report && (
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
                    <span className={`badge ${f.severity === "high" ? "hot" : f.severity === "medium" ? "warm" : "cold"}`}>{f.severity}</span>{" "}
                    <span className="muted">{f.detail}</span>
                  </div>
                ))}
                {(report.dns || report.shodan) && (
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
                )}
              </div>
            </div>
          )}

          {report?.email_draft && (
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
                <button className="btn btn-sm" onClick={sendPitch} disabled={sending || !sendTo.trim()} data-testid="threat-send-email">
                  {sending ? <span className="spinner" /> : <><Send size={13} /> Send via Gmail</>}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="section-title">High-Ticket Targets ({reports.filter((r) => r.high_ticket).length})</div>
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
    </div>
  );
}

/* ============================ ENRICHMENT ENGINE ============================ */
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

const TOOLS = [
  { id: "dns", name: "DNS Recon", icon: Server, desc: "A / MX / NS / TXT records", field: "target", ph: "example.com" },
  { id: "whois", name: "WHOIS Lookup", icon: FileSearch, desc: "Domain registration intel", field: "target", ph: "example.com" },
  { id: "ip", name: "IP Lookup", icon: Globe, desc: "Geo + ASN for any IP", field: "target", ph: "8.8.8.8" },
  { id: "geolocate", name: "Geolocate", icon: MapPin, desc: "Resolve host → geo", field: "target", ph: "example.com" },
  { id: "phone", name: "Phone Intel", icon: Smartphone, desc: "Carrier + region + validity", field: "target", ph: "+14085551234" },
  { id: "social", name: "Social Scan", icon: AtSign, desc: "Username across platforms", field: "target", ph: "username" },
  { id: "breach", name: "Breach Check", icon: ShieldAlert, desc: "Exposure lookup", field: "target", ph: "email@x.com" },
  { id: "subdomains", name: "Subdomains", icon: Network, desc: "Common subdomain enum", field: "target", ph: "example.com" },
  { id: "portscan", name: "Port Scan", icon: ScanLine, desc: "Common open ports", field: "target", ph: "scanme.nmap.org" },
  { id: "metadata", name: "Page Metadata", icon: FileSearch, desc: "Emails + phones from URL", field: "url", ph: "https://example.com" },
  { id: "dork", name: "Google Dork", icon: Search, desc: "Search operator query", field: "dork", ph: 'site:gov filetype:pdf' },
  { id: "shodan", name: "Shodan", icon: Crosshair, desc: "Device search (needs key)", field: "query", ph: "apache country:US" },
];

export function Osint() {
  const [active, setActive] = useState(TOOLS[0]);
  const [val, setVal] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [out, setOut] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!val.trim()) return;
    setBusy(true); setOut(null);
    try {
      const body = { [active.field]: val.trim() };
      if (active.id === "shodan") body.api_key = apiKey;
      const r = await api.post(`/osint/${active.id}`, body);
      setOut(r.data);
    } catch (e) { setOut({ error: e.response?.data?.detail || e.message }); }
    finally { setBusy(false); }
  };

  return (
    <div className="fade-in">
      <div className="section-title">Reconnaissance Toolkit</div>
      <div className="osint-grid">
        {TOOLS.map((t) => {
          const Ico = t.icon;
          return (
            <div key={t.id} className={`tool-card ${active.id === t.id ? "active" : ""}`}
              onClick={() => { setActive(t); setOut(null); setVal(""); }} data-testid={`tool-${t.id}`}>
              <div className="ico"><Ico size={18} /></div>
              <h4>{t.name}</h4>
              <p>{t.desc}</p>
            </div>
          );
        })}
      </div>

      <div className="panel" style={{ marginTop: 22 }}>
        <div className="panel-head"><h3>{active.name}</h3><span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>POST /api/osint/{active.id}</span></div>
        <div className="panel-body">
          <div className="toolbar" style={{ marginBottom: 16 }}>
            <input className="search-input" style={{ flex: 1, minWidth: 240 }} placeholder={active.ph}
              value={val} onChange={(e) => setVal(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run()}
              data-testid="osint-input" />
            {active.id === "shodan" && (
              <input className="search-input" placeholder="Shodan API key" value={apiKey}
                onChange={(e) => setApiKey(e.target.value)} data-testid="osint-shodan-key" />
            )}
            <button className="btn btn-sm" onClick={run} disabled={busy} data-testid="osint-run">
              {busy ? <span className="spinner" /> : <><Crosshair size={14} /> Execute</>}
            </button>
          </div>
          <div className="result-box" data-testid="osint-result">
            {out ? JSON.stringify(out, null, 2) : <span className="placeholder">// awaiting target — results render here as JSON</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================ AI CHAT ============================ */
export function AIChat() {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("deepseek");
  const [busy, setBusy] = useState(false);
  const streamRef = useRef(null);
  useEffect(() => { streamRef.current?.scrollTo(0, streamRef.current.scrollHeight); }, [msgs, busy]);

  const send = async () => {
    const m = input.trim();
    if (!m || busy) return;
    setMsgs((x) => [...x, { id: crypto.randomUUID(), role: "user", text: m }]); setInput(""); setBusy(true);
    try {
      const r = await api.post("/enrichment/chat", { message: m, model });
      setMsgs((x) => [...x, { id: crypto.randomUUID(), role: "ai", text: r.data.response || ("⚠ " + (r.data.error || "no response")) }]);
    } catch (e) {
      setMsgs((x) => [...x, { id: crypto.randomUUID(), role: "ai", text: "⚠ " + (e.response?.data?.detail || e.message) }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 10 }}>NEXUS AI · Analyst</span>
      </div>
      <div className="panel">
        <div className="panel-head">
          <h3>Conversation</h3>
          <select className="select" value={model} onChange={(e) => setModel(e.target.value)} data-testid="chat-model">
            <option value="deepseek">DeepSeek V3.1</option>
            <option value="qwen">Qwen 2.5 32B</option>
          </select>
        </div>
        <div className="chat-wrap">
          <div className="chat-stream" ref={streamRef}>
            {!msgs.length && (
              <div className="chat-empty">
                <Bot size={42} />
                <div className="mono" style={{ fontSize: 13 }}>Ask about leads, OSINT strategy or digital footprints.</div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={m.id} className={`msg ${m.role}`} data-testid={`chat-msg-${i}`}>
                {m.role === "ai" && <span className="who">NEXUS</span>}{m.text}
              </div>
            ))}
            {busy && <div className="msg ai"><span className="who">NEXUS</span><span className="spinner lime" /></div>}
          </div>
          <div className="chat-input-row">
            <input className="search-input" style={{ flex: 1 }} placeholder="Message NEXUS…"
              value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
              data-testid="chat-input" />
            <button className="btn btn-sm" onClick={send} disabled={busy} data-testid="chat-send"><Send size={14} /></button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================ API KEYS ============================ */
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

/* ============================ REPORTS ============================ */
export function Reports() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = () => { setLoading(true); api.get("/osint/reports").then((r) => setRows(r.data)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);
  return (
    <div className="fade-in">
      <div className="section-title">Intel Reports Log</div>
      <div className="panel">
        <div className="panel-head"><h3>Recent OSINT Executions</h3>
          <button className="btn btn-ghost btn-sm" onClick={load}><RefreshCw size={13} /></button></div>
        <div className="panel-body" style={{ padding: 0 }}>
          <table className="tbl">
            <thead><tr><th>ID</th><th>Target</th><th>Tool</th><th>Timestamp</th></tr></thead>
            <tbody>
              {loading ? <tr><td colSpan={4} style={{ padding: 30, textAlign: "center" }}><span className="spinner lime" /></td></tr>
              : rows.map((r) => (
                <tr key={r.id}>
                  <td className="muted">{r.id.slice(-6)}</td>
                  <td className="name">{r.target}</td>
                  <td><span className="badge">{r.tool}</span></td>
                  <td className="muted">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
              {!loading && !rows.length && <tr><td colSpan={4} className="empty">No reports yet — run an OSINT tool.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* Scrapers moved to ./Scrapers.jsx */

const GOV_ROLES = ["user", "analyst", "tenant_admin", "admin", "owner"];

function MonitorPanel() {
  const [m, setM] = useState(null);
  const [err, setErr] = useState("");
  const load = () => api.get("/admin/monitoring").then((r) => setM(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message));
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);
  if (err) return <div className="empty"><ShieldAlert size={28} /><div>{err}</div></div>;
  if (!m) return <div className="empty"><RefreshCw size={28} className="spin" /><div>Loading telemetry…</div></div>;
  const cards = [
    { k: "DB", v: m.db_connected ? "Connected" : "DOWN", ok: m.db_connected, icon: Database },
    { k: "Scheduler", v: m.scheduler_running ? "Running" : "Stopped", ok: m.scheduler_running, icon: Activity },
    { k: "Tenants", v: m.tenants, icon: Building2 },
    { k: "Users", v: m.users, icon: Users },
    { k: "Leads (live)", v: m.leads_available, icon: Boxes },
    { k: "Leads sold", v: m.leads_sold, icon: CreditCard },
    { k: "Audit events 24h", v: m.audit_events_24h, icon: ScrollText },
    { k: "Failed logins 24h", v: m.logins_failed_24h, ok: m.logins_failed_24h === 0, icon: ShieldAlert },
    { k: "Locked identities", v: m.locked_identities, ok: m.locked_identities === 0, icon: ShieldCheck },
  ];
  return (
    <div className="fade-in" data-testid="gov-monitoring">
      <div className="grid-stats" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))", gap: 12 }}>
        {cards.map((c) => {
          const Ico = c.icon;
          return (
            <div key={c.k} className="panel" style={{ padding: 16 }} data-testid={`monitor-${c.k.replace(/\s+/g, "-").toLowerCase()}`}>
              <div className="muted" style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}><Ico size={14} /> {c.k}</div>
              <div style={{ fontSize: 22, fontWeight: 700, marginTop: 6, color: c.ok === false ? "var(--danger,#ef4444)" : c.ok === true ? "var(--accent)" : "inherit" }}>{c.v}</div>
            </div>
          );
        })}
      </div>
      <div className="muted" style={{ marginTop: 12, fontSize: 12 }}>
        AI provider: <b>{m.ai_provider}</b> · checked {m.checked_at ? new Date(m.checked_at).toLocaleTimeString() : "—"} · auto-refresh 15s
      </div>
    </div>
  );
}

function TenantsPanel() {
  const [t, setT] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => { api.get("/admin/tenants").then((r) => setT(r.data.tenants)).catch((e) => setErr(e.response?.data?.detail || e.message)); }, []);
  if (err) return <div className="empty"><ShieldAlert size={28} /><div>{err}</div></div>;
  return (
    <div className="panel" data-testid="gov-tenants">
      <div className="panel-head"><h3><Building2 size={15} style={{ verticalAlign: -2, marginRight: 8 }} />Tenants ({t.length})</h3></div>
      <div className="panel-body" style={{ padding: 0 }}>
        <table className="tbl">
          <thead><tr><th>Organization</th><th>Owner</th><th>Members</th><th>Status</th><th>Tenant ID</th></tr></thead>
          <tbody>
            {t.map((x) => (
              <tr key={x.tenant_id} data-testid={`tenant-${x.tenant_id}`}>
                <td className="name">{x.name}</td>
                <td className="muted">{x.owner_email}</td>
                <td>{x.members}</td>
                <td><span className={`badge ${x.status === "active" ? "" : "hot"}`}>{x.status}</span></td>
                <td className="muted mono" style={{ fontSize: 11 }}>{x.tenant_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AuditPanel() {
  const [data, setData] = useState({ logs: [], actions: [] });
  const [filter, setFilter] = useState("");
  const [err, setErr] = useState("");
  const load = (action) => api.get(`/admin/audit?limit=200${action ? `&action=${action}` : ""}`).then((r) => setData(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message));
  useEffect(() => { load(filter); }, [filter]);
  if (err) return <div className="empty"><ShieldAlert size={28} /><div>{err}</div></div>;
  return (
    <div className="panel" data-testid="gov-audit">
      <div className="panel-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3><ScrollText size={15} style={{ verticalAlign: -2, marginRight: 8 }} />Audit Trail</h3>
        <select className="select" value={filter} onChange={(e) => setFilter(e.target.value)} data-testid="audit-action-filter">
          <option value="">All actions</option>
          {data.actions.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>
      <div className="panel-body" style={{ padding: 0, maxHeight: 520, overflow: "auto" }}>
        <table className="tbl">
          <thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Tenant</th><th>Status</th><th>Detail</th></tr></thead>
          <tbody>
            {data.logs.map((l) => (
              <tr key={l.id} data-testid={`audit-row-${l.id}`}>
                <td className="muted" style={{ fontSize: 11, whiteSpace: "nowrap" }}>{l.created_at ? new Date(l.created_at).toLocaleString() : "—"}</td>
                <td><span className="badge">{l.action}</span></td>
                <td className="muted">{l.user_email || "—"}</td>
                <td className="muted mono" style={{ fontSize: 11 }}>{l.tenant_id || "—"}</td>
                <td><span className={`badge ${l.status === "success" ? "" : "hot"}`}>{l.status}</span></td>
                <td className="muted" style={{ fontSize: 11 }}>{l.target || ""} {l.meta && Object.keys(l.meta).length ? JSON.stringify(l.meta) : ""}</td>
              </tr>
            ))}
            {data.logs.length === 0 && <tr><td colSpan={6} className="muted" style={{ padding: 20, textAlign: "center" }}>No audit events yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OutreachPanel() {
  const [cfg, setCfg] = useState({ enabled: false, category: "real_estate", subject: "", body: "", from_name: "Robert Burke", min_score: 0 });
  const [history, setHistory] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [sandboxTo, setSandboxTo] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const loadHistory = () => api.get("/outreach/history").then((r) => setHistory(r.data.sends || [])).catch(() => {});
  useEffect(() => {
    api.get("/outreach/auto").then((r) => { if (r.data && r.data.subject !== undefined) setCfg((c) => ({ ...c, ...r.data })); }).catch(() => {});
    api.get("/outreach/templates").then((r) => setTemplates(r.data.templates || [])).catch(() => {});
    loadHistory();
  }, []);
  const applyTemplate = (id) => {
    const t = templates.find((x) => x.id === id);
    if (t) { setCfg((c) => ({ ...c, subject: t.subject, body: t.body })); setMsg(`Loaded template: ${t.label}`); }
  };
  const sandbox = async () => {
    if (!sandboxTo.trim()) { setMsg("Enter a sandbox email to receive the test."); return; }
    setBusy(true); setMsg("Sending sandbox test…");
    try {
      const r = await api.post("/outreach/send", { subject: cfg.subject, body: cfg.body, from_name: cfg.from_name, category: cfg.category, test_to: sandboxTo.trim() });
      setMsg(`Sandbox test sent to ${r.data.to} (sample: ${r.data.sample_company}).`);
    } catch (e) { setMsg(e.response?.data?.detail || e.message); }
    setBusy(false);
  };
  const save = async () => { setBusy(true); setMsg(""); try { await api.put("/outreach/auto", cfg); setMsg("Auto-send settings saved."); } catch (e) { setMsg(e.response?.data?.detail || e.message); } setBusy(false); };
  const runNow = async () => { setBusy(true); setMsg(""); try { const r = await api.post("/outreach/auto/run"); setMsg(`Auto sweep: ${r.data.sent || 0} sent, ${r.data.failed || 0} failed.`); loadHistory(); } catch (e) { setMsg(e.response?.data?.detail || e.message); } setBusy(false); };
  const enrich = async () => {
    setBusy(true); setMsg("Enriching emails from lead websites…");
    try {
      const r = await api.post("/outreach/enrich-emails", { category: cfg.category, only_hq: true, limit: 150 });
      const job = r.data.job_id;
      const poll = setInterval(async () => {
        try {
          const st = (await api.get(`/outreach/enrich-status/${job}`)).data;
          setMsg(`Enriching ${st.done}/${st.total} · found ${st.found} emails…`);
          if (st.status === "complete") { clearInterval(poll); setMsg(`Enrichment done — found ${st.found} new emails. Run auto-send to reach them.`); setBusy(false); }
        } catch { clearInterval(poll); setBusy(false); }
      }, 4000);
    } catch (e) { setMsg(e.response?.data?.detail || e.message); setBusy(false); }
  };
  const sent = history.filter((h) => h.status === "sent").length;
  return (
    <div className="panel" data-testid="gov-outreach">
      <div className="panel-head"><h3><Mail size={15} style={{ verticalAlign: -2, marginRight: 8 }} />Outreach Engine</h3></div>
      <div className="panel-body" style={{ display: "grid", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <select className="select" onChange={(e) => e.target.value && applyTemplate(e.target.value)} defaultValue="" data-testid="outreach-template">
            <option value="">Load pilot template…</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
          <a className="status-pill" href="/launch/compare.html" target="_blank" rel="noreferrer" style={{ textDecoration: "none" }} data-testid="outreach-compare-link"><Wand2 size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Model &amp; comparison doc</a>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }} data-testid="outreach-auto-toggle">
            <input type="checkbox" checked={!!cfg.enabled} onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })} />
            <span><Zap size={13} style={{ verticalAlign: -2, marginRight: 4 }} />Auto-send to new HQ leads {cfg.enabled ? "(ON)" : "(off)"}</span>
          </label>
          <input className="input" style={{ width: 150 }} value={cfg.category} onChange={(e) => setCfg({ ...cfg, category: e.target.value })} placeholder="category" data-testid="outreach-category" />
          <input className="input" style={{ width: 160 }} value={cfg.from_name} onChange={(e) => setCfg({ ...cfg, from_name: e.target.value })} placeholder="From name" data-testid="outreach-fromname" />
        </div>
        <input className="input" value={cfg.subject} onChange={(e) => setCfg({ ...cfg, subject: e.target.value })} placeholder="Email subject (supports [First Name], {{company}}, {{city}})" data-testid="outreach-subject" />
        <textarea className="input" style={{ minHeight: 150, fontFamily: "inherit" }} value={cfg.body} onChange={(e) => setCfg({ ...cfg, body: e.target.value })} placeholder="Email body — tokens: [First Name], {{company}}, {{city}}, {{category}}" data-testid="outreach-body" />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="status-pill" style={{ cursor: "pointer" }} onClick={save} disabled={busy} data-testid="outreach-save"><ShieldCheck size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Save settings</button>
          <button className="status-pill" style={{ cursor: "pointer" }} onClick={enrich} disabled={busy} data-testid="outreach-enrich"><Wand2 size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Enrich emails</button>
          <button className="status-pill" style={{ cursor: "pointer" }} onClick={runNow} disabled={busy} data-testid="outreach-run"><Send size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Send now</button>
          <button className="status-pill" style={{ cursor: "pointer" }} onClick={loadHistory} data-testid="outreach-refresh"><RefreshCw size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Refresh</button>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input className="input" style={{ width: 240 }} value={sandboxTo} onChange={(e) => setSandboxTo(e.target.value)} placeholder="Sandbox test → your email" data-testid="outreach-sandbox-email" />
          <button className="status-pill" style={{ cursor: "pointer" }} onClick={sandbox} disabled={busy} data-testid="outreach-sandbox-send"><Mail size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Send sandbox test</button>
        </div>
        {msg && <div className="muted" style={{ fontSize: 12 }} data-testid="outreach-msg">{msg}</div>}
        <div style={{ fontSize: 12 }} className="muted">Total emails sent: <strong>{sent}</strong></div>
        <div style={{ maxHeight: 320, overflow: "auto", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8 }}>
          <table className="tbl">
            <thead><tr><th>Status</th><th>Type</th><th>Company</th><th>Email</th></tr></thead>
            <tbody>
              {history.slice(0, 200).map((h) => (
                <tr key={h.id} data-testid={`outreach-send-${h.id}`}>
                  <td><span className="badge">{h.status}</span></td>
                  <td className="muted">{h.auto ? "auto" : "manual"}</td>
                  <td className="name">{h.company || "—"}</td>
                  <td className="muted">{h.email}</td>
                </tr>
              ))}
              {history.length === 0 && <tr><td colSpan={4} className="muted" style={{ padding: 18, textAlign: "center" }}>No emails sent yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function PilotLeadsPanel() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    api.get("/waitlist").then((r) => setRows(r.data.requests || [])).catch((e) => setErr(e.response?.data?.detail || e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);
  const exportCsv = () => {
    const header = ["email", "company", "source", "captured_at"];
    const lines = [header.join(",")].concat(
      rows.map((r) => header.map((h) => `"${String(r[h] ?? "").replace(/"/g, '""')}"`).join(","))
    );
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `pilot-leads-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };
  if (err) return <div className="empty"><ShieldAlert size={28} /><div>{err}</div></div>;
  return (
    <div className="panel" data-testid="gov-pilot-leads">
      <div className="panel-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3><Inbox size={15} style={{ verticalAlign: -2, marginRight: 8 }} />Pilot Leads ({rows.length})</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="status-pill" style={{ cursor: "pointer" }} onClick={load} data-testid="pilot-refresh"><RefreshCw size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Refresh</button>
          <button className="status-pill" style={{ cursor: "pointer" }} onClick={exportCsv} disabled={!rows.length} data-testid="pilot-export-csv"><Download size={13} style={{ marginRight: 6, verticalAlign: -2 }} />Export CSV</button>
        </div>
      </div>
      <div className="panel-body" style={{ padding: 0, maxHeight: 560, overflow: "auto" }}>
        <table className="tbl">
          <thead><tr><th>Email</th><th>Company</th><th>Source</th><th>Captured</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-testid={`pilot-lead-${r.id}`}>
                <td className="name">{r.email}</td>
                <td className="muted">{r.company || "—"}</td>
                <td><span className="badge">{r.source || "launch_site"}</span></td>
                <td className="muted" style={{ fontSize: 11, whiteSpace: "nowrap" }}>{r.captured_at ? new Date(r.captured_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
            {!loading && rows.length === 0 && <tr><td colSpan={4} className="muted" style={{ padding: 20, textAlign: "center" }}>No pilot requests yet. Signups from the launch site appear here.</td></tr>}
            {loading && <tr><td colSpan={4} className="muted" style={{ padding: 20, textAlign: "center" }}><RefreshCw size={16} className="spin" /> Loading…</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Admin() {
  const [section, setSection] = useState("operators");
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const load = () => api.get("/admin/users").then((r) => setUsers(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message));
  useEffect(() => { if (section === "operators") load(); }, [section]);
  const setRole = async (id, role) => { await api.patch(`/admin/users/${id}/role`, { role }); load(); };

  const SECTIONS = [
    { id: "operators", label: "Operators", icon: Users },
    { id: "tenants", label: "Tenants", icon: Building2 },
    { id: "audit", label: "Audit Trail", icon: ScrollText },
    { id: "monitoring", label: "Monitoring", icon: Activity },
    { id: "pilot", label: "Pilot Leads", icon: Inbox },
    { id: "outreach", label: "Outreach", icon: Mail },
  ];

  return (
    <div className="fade-in">
      <div className="section-title">Governance Console</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {SECTIONS.map((s) => {
          const Ico = s.icon;
          return (
            <button key={s.id} className={`status-pill ${section === s.id ? "active" : ""}`}
              style={{ cursor: "pointer", borderColor: section === s.id ? "var(--accent)" : undefined, color: section === s.id ? "var(--accent)" : undefined }}
              onClick={() => setSection(s.id)} data-testid={`gov-tab-${s.id}`}>
              <Ico size={13} style={{ marginRight: 6, verticalAlign: -2 }} />{s.label}
            </button>
          );
        })}
      </div>

      {section === "operators" && (err ? <div className="empty"><ShieldAlert size={36} /><div>{err}</div></div> : (
        <div className="panel" data-testid="gov-operators">
          <div className="panel-head"><h3><Users size={15} style={{ verticalAlign: -2, marginRight: 8 }} />All Operators ({users.length})</h3></div>
          <div className="panel-body" style={{ padding: 0 }}>
            <table className="tbl">
              <thead><tr><th>Operator</th><th>Email</th><th>Tenant</th><th>Role</th><th>Credits</th><th>Assign role</th></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} data-testid={`admin-user-${u.id}`}>
                    <td className="name">{u.name}</td>
                    <td className="muted">{u.email}</td>
                    <td className="muted">{u.tenant_name || u.tenant_id}</td>
                    <td><span className={`badge ${["admin", "owner"].includes(u.role) ? "hot" : ""}`}>{u.role}</span></td>
                    <td>{u.credits ?? 0}</td>
                    <td>
                      <select className="select" value={u.role} onChange={(e) => setRole(u.id, e.target.value)} data-testid={`admin-role-${u.id}`}>
                        {GOV_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      {section === "tenants" && <TenantsPanel />}
      {section === "audit" && <AuditPanel />}
      {section === "monitoring" && <MonitorPanel />}
      {section === "pilot" && <PilotLeadsPanel />}
      {section === "outreach" && <OutreachPanel />}
    </div>
  );
}
