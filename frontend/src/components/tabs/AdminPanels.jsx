import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import {
  RefreshCw, ShieldAlert, ShieldCheck, Database, Activity, Building2, Users,
  Boxes, CreditCard, ScrollText, Inbox, Download, Mail, Zap, Wand2, Send,
} from "lucide-react";

export function MonitorPanel() {
  const [m, setM] = useState(null);
  const [err, setErr] = useState("");
  const load = () => api.get("/admin/monitoring").then((r) => setM(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message));
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only poll; `load` is stable in intent
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

export function TenantsPanel() {
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

export function AuditPanel() {
  const [data, setData] = useState({ logs: [], actions: [] });
  const [filter, setFilter] = useState("");
  const [err, setErr] = useState("");
  const load = (action) => api.get(`/admin/audit?limit=200${action ? `&action=${action}` : ""}`).then((r) => setData(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message));
  // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only when `filter` changes
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

export function OutreachPanel() {
  const [cfg, setCfg] = useState({ enabled: false, category: "real_estate", subject: "", body: "", from_name: "Robert Burke", min_score: 0 });
  const [history, setHistory] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [sandboxTo, setSandboxTo] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const loadHistory = () => api.get("/outreach/history").then((r) => setHistory(r.data.sends || [])).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only initial load
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

export function PilotLeadsPanel() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    api.get("/waitlist").then((r) => setRows(r.data.requests || [])).catch((e) => setErr(e.response?.data?.detail || e.message)).finally(() => setLoading(false));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only initial load
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
