import React, { useEffect, useState, useRef } from "react";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { cat, scoreClass } from "./helpers";
import {
  Send, Bot, Trash2, RefreshCw, Plus, KeyRound,
  Copy, ShieldAlert, Crosshair, Globe, Network, Smartphone, AtSign,
  MapPin, ScanLine, Server, FileSearch, Search, Users,
  CreditCard, UserSearch, ShieldCheck, AlertTriangle, Boxes
} from "lucide-react";

/* ============================ OVERVIEW ============================ */
export function Overview({ goTo }) {
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  useEffect(() => {
    api.get("/leads/stats").then((r) => setStats(r.data)).catch(() => {});
    api.get("/leads?limit=5").then((r) => setLeads(r.data.leads)).catch(() => {});
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
                    <td className="name">{l.full_name || "—"}<div className="muted">{l.city}, {l.state}</div></td>
                    <td><span className={`badge ${scoreClass(l.score)}`}>{Math.round(l.score)}</span></td>
                  </tr>
                ))}
                {!leads.length && <tr><td className="muted" style={{ padding: 22 }}>No leads yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================ LEADS ============================ */
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
    setMsgs((x) => [...x, { role: "user", text: m }]); setInput(""); setBusy(true);
    try {
      const r = await api.post("/enrichment/chat", { message: m, model });
      setMsgs((x) => [...x, { role: "ai", text: r.data.response || ("⚠ " + (r.data.error || "no response")) }]);
    } catch (e) {
      setMsgs((x) => [...x, { role: "ai", text: "⚠ " + (e.response?.data?.detail || e.message) }]);
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
              <div key={i} className={`msg ${m.role}`} data-testid={`chat-msg-${i}`}>
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

export function Admin() {
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const load = () => api.get("/admin/users").then((r) => setUsers(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message));
  useEffect(() => { load(); }, []);
  const setRole = async (id, role) => { await api.patch(`/admin/users/${id}/role`, { role }); load(); };

  if (err) return <div className="empty"><ShieldAlert size={36} /><div>{err}</div></div>;
  return (
    <div className="fade-in">
      <div className="section-title">Admin · Operator Management</div>
      <div className="panel">
        <div className="panel-head"><h3><Users size={15} style={{ verticalAlign: -2, marginRight: 8 }} />All Operators</h3></div>
        <div className="panel-body" style={{ padding: 0 }}>
          <table className="tbl">
            <thead><tr><th>Operator</th><th>Email</th><th>Role</th><th>Joined</th><th></th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} data-testid={`admin-user-${u.id}`}>
                  <td className="name">{u.name}</td>
                  <td className="muted">{u.email}</td>
                  <td><span className={`badge ${u.role === "admin" ? "hot" : ""}`}>{u.role}</span></td>
                  <td className="muted">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
                  <td>
                    <select className="select" value={u.role} onChange={(e) => setRole(u.id, e.target.value)} data-testid={`admin-role-${u.id}`}>
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
