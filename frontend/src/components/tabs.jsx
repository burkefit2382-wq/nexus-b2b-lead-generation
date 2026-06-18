import React, { useEffect, useState, useRef } from "react";
import api from "../lib/api";
import {
  Send, Bot, Trash2, DollarSign, Download, RefreshCw, Plus, KeyRound,
  Copy, ShieldAlert, Crosshair, Globe, Network, Smartphone, AtSign,
  MapPin, ScanLine, Server, FileSearch, Search, Users, Sparkles
} from "lucide-react";

const cat = (c) => (c === "home_remodeling" ? "Remodeling" : c === "cleaning" ? "Cleaning" : c || "—");
const scoreClass = (s) => (s >= 70 ? "hot" : s >= 45 ? "warm" : "cold");

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
export function Leads() {
  const [data, setData] = useState({ leads: [], total: 0 });
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [enriching, setEnriching] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const p = new URLSearchParams();
    if (search) p.set("search", search);
    if (category) p.set("category", category);
    api.get(`/leads?${p.toString()}`).then((r) => setData(r.data)).finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [category]);

  const enrichAll = async () => {
    setEnriching(true);
    try { await api.post("/enrichment/enrich", { batch: true, limit: 10 }); load(); }
    catch (e) { alert("Enrichment error: " + (e.response?.data?.error || e.message)); }
    finally { setEnriching(false); }
  };
  const sell = async (id) => {
    const price = prompt("Sale price ($):", "150");
    if (price == null) return;
    await api.patch(`/leads/${id}/sell?price=${parseFloat(price) || 0}`); load();
  };
  const del = async (id) => { if (window.confirm("Delete this lead?")) { await api.delete(`/leads/${id}`); load(); } };
  const exportCsv = () => window.open(`${api.defaults.baseURL}/leads/export/csv`, "_blank");

  return (
    <div className="fade-in">
      <div className="section-title">Lead Engine · {data.total} records</div>
      <div className="panel">
        <div className="panel-head">
          <div className="toolbar">
            <input className="search-input" placeholder="Search name, email, city…" value={search}
              onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()}
              data-testid="leads-search" />
            <select className="select" value={category} onChange={(e) => setCategory(e.target.value)} data-testid="leads-category">
              <option value="">All categories</option>
              <option value="home_remodeling">Remodeling</option>
              <option value="cleaning">Cleaning</option>
            </select>
            <button className="btn btn-ghost btn-sm" onClick={load} data-testid="leads-refresh"><Search size={14} /></button>
          </div>
          <div className="toolbar">
            <button className="btn btn-ghost btn-sm" onClick={exportCsv} data-testid="leads-export"><Download size={14} /> CSV</button>
            <button className="btn btn-sm" onClick={enrichAll} disabled={enriching} data-testid="leads-enrich-all">
              {enriching ? <span className="spinner" /> : <><Sparkles size={14} /> Enrich AI</>}
            </button>
          </div>
        </div>
        <div className="panel-body" style={{ padding: 0, overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr>
              <th>Lead</th><th>Contact</th><th>Category</th><th>Score</th><th>AI Summary</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
              {loading ? <tr><td colSpan={7} style={{ padding: 30, textAlign: "center" }}><span className="spinner lime" /></td></tr>
              : data.leads.map((l) => (
                <tr key={l.id} data-testid={`lead-row-${l.id}`}>
                  <td className="name">{l.full_name || "—"}<div className="muted">{l.city}{l.state ? ", " + l.state : ""}</div></td>
                  <td className="muted">{l.email || "—"}<div>{l.phone}</div></td>
                  <td><span className="badge">{cat(l.category)}</span></td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className={`badge ${scoreClass(l.score)}`}>{Math.round(l.score)}</span>
                      <div className="score-bar"><i style={{ width: `${Math.min(l.score, 100)}%` }} /></div>
                    </div>
                  </td>
                  <td className="muted" style={{ maxWidth: 260, fontSize: 13 }}>{l.ai_summary || <span style={{ opacity: .5 }}>not enriched</span>}{l.ai_budget_est && <div style={{ color: "var(--accent)", marginTop: 4 }}>{l.ai_budget_est}</div>}</td>
                  <td><span className={`badge ${l.is_sold ? "sold" : ""}`}>{l.status}</span></td>
                  <td>
                    <div className="row-actions">
                      <button className="icon-btn" title="Mark sold" onClick={() => sell(l.id)} data-testid={`lead-sell-${l.id}`}><DollarSign size={14} /></button>
                      <button className="icon-btn danger" title="Delete" onClick={() => del(l.id)} data-testid={`lead-del-${l.id}`}><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && !data.leads.length && <tr><td colSpan={7} className="empty">No leads match your filters.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ============================ OSINT TOOLS ============================ */
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
  const [busy, setBusy] = useState(false);
  const streamRef = useRef(null);
  useEffect(() => { streamRef.current?.scrollTo(0, streamRef.current.scrollHeight); }, [msgs, busy]);

  const send = async () => {
    const m = input.trim();
    if (!m || busy) return;
    setMsgs((x) => [...x, { role: "user", text: m }]); setInput(""); setBusy(true);
    try {
      const r = await api.post("/enrichment/chat", { message: m });
      setMsgs((x) => [...x, { role: "ai", text: r.data.response || ("⚠ " + (r.data.error || "no response")) }]);
    } catch (e) {
      setMsgs((x) => [...x, { role: "ai", text: "⚠ " + (e.response?.data?.detail || e.message) }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="fade-in">
      <div className="section-title">NEXUS AI · DeepSeek Analyst</div>
      <div className="panel">
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

/* ============================ ADMIN ============================ */
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
