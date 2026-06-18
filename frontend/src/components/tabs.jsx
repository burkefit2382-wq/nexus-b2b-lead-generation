import React, { useEffect, useState, useRef } from "react";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";
import {
  Send, Bot, Trash2, DollarSign, Download, RefreshCw, Plus, KeyRound,
  Copy, ShieldAlert, Crosshair, Globe, Network, Smartphone, AtSign,
  MapPin, ScanLine, Server, FileSearch, Search, Users, Sparkles,
  Lock, Unlock, CreditCard, UserSearch, ShieldCheck, AlertTriangle
} from "lucide-react";

const CATEGORY_LABELS = { home_remodeling: "Remodeling", cleaning: "Cleaning" };
const cat = (c) => CATEGORY_LABELS[c] || c || "—";
const scoreClass = (s) => {
  if (s >= 70) return "hot";
  if (s >= 45) return "warm";
  return "cold";
};

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
  const { user, refreshUser } = useAuth();
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
  const unlock = async (id) => {
    try { await api.post(`/leads/${id}/unlock`); await refreshUser(); load(); }
    catch (e) {
      if (e.response?.status === 402) { if (window.confirm("Out of credits. Go to Billing to buy a pack?")) window.dispatchEvent(new CustomEvent("nexus-goto", { detail: "billing" })); }
      else alert(e.response?.data?.detail || e.message);
    }
  };
  const del = async (id) => { if (window.confirm("Delete this lead?")) { await api.delete(`/leads/${id}`); load(); } };
  const exportCsv = () => window.open(`${api.defaults.baseURL}/leads/export/csv`, "_blank");

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span>Lead Engine · {data.total} records</span>
        <span className="mono" style={{ fontSize: 12, color: "var(--accent)" }}>
          <CreditCard size={13} style={{ verticalAlign: -2, marginRight: 6 }} />{user?.credits ?? 0} credits
        </span>
      </div>
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
                  <td className="muted">
                    {l.locked ? <span style={{ color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 12 }}><Lock size={12} style={{ verticalAlign: -1, marginRight: 5 }} />locked</span>
                      : <>{l.email || "—"}<div>{l.phone}</div></>}
                  </td>
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
                      {l.locked && <button className="icon-btn" style={{ color: "var(--accent)", borderColor: "var(--accent-dim)" }} title="Unlock (1 credit)" onClick={() => unlock(l.id)} data-testid={`lead-unlock-${l.id}`}><Unlock size={14} /></button>}
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
                    {(report.ai_profile.interests || []).map((t, i) => <span key={i} className="badge cold">{t}</span>)}
                  </div>
                </div>
                <div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>DIGITAL FOOTPRINT ({report.footprint.accounts.length})</div>
                  {report.footprint.accounts.length ? report.footprint.accounts.map((a, i) => (
                    <a key={i} href={a.url} target="_blank" rel="noreferrer" className="key-row" style={{ marginBottom: 8, display: "flex" }}>
                      <div className="kmeta"><b>{a.platform}</b><div className="pfx">{a.url}</div></div>
                      <span className="badge hot">{(a.confidence * 100).toFixed(0)}%</span>
                    </a>
                  )) : <div className="muted mono" style={{ fontSize: 12 }}>No public accounts detected.</div>}
                </div>
                <div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>PUBLIC RECORDS ({report.public_records.records.length})</div>
                  {report.public_records.records.map((r, i) => (
                    <div key={i} style={{ fontSize: 13, padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                      <span className="badge">{r.category}</span> <span className="muted">{r.description}</span>
                    </div>
                  ))}
                </div>
                {report.risk.reasons.length > 0 && (
                  <div>
                    <div className="mono" style={{ fontSize: 11, color: "var(--danger)", marginBottom: 8 }}>RISK INDICATORS</div>
                    {report.risk.reasons.map((r, i) => <div key={i} style={{ fontSize: 13, color: "var(--amber)" }}>⚠ {r}</div>)}
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
        setPoll("✅ Payment complete — credits added!");
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

/* ============================ SCRAPERS (24/7 engine) ============================ */
export function Scrapers() {
  const [status, setStatus] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [feed, setFeed] = useState([]);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const loadStatus = () => api.get("/scraper/status").then((r) => setStatus(r.data)).catch(() => {});
  const loadFeed = () => api.get("/scraper/feed?limit=12").then((r) => setFeed(r.data)).catch(() => {});
  const loadCfg = () => api.get("/scraper/config").then((r) => setCfg(r.data)).catch(() => {});
  useEffect(() => {
    loadStatus(); loadCfg(); loadFeed();
    const t = setInterval(() => { loadStatus(); loadFeed(); }, 8000);
    return () => clearInterval(t);
  }, []);

  const trigger = async () => {
    setTriggering(true);
    try { await api.post("/scraper/trigger"); setTimeout(() => { loadStatus(); loadFeed(); }, 6000); }
    finally { setTimeout(() => setTriggering(false), 6000); }
  };
  const save = async () => {
    setSaving(true);
    try { await api.put("/scraper/config", cfg); loadStatus(); }
    catch (e) { alert("Save failed: " + (e.response?.data?.detail || e.message)); }
    finally { setSaving(false); }
  };
  const upd = (k, v) => setCfg((c) => ({ ...c, [k]: v }));
  const updSrc = (i, k, v) => setCfg((c) => { const s = [...c.sources]; s[i] = { ...s[i], [k]: v }; return { ...c, sources: s }; });
  const addSrc = () => setCfg((c) => ({ ...c, sources: [...c.sources, { provider: "hackernews", query: "", subreddit: "", category: "services" }] }));
  const delSrc = (i) => setCfg((c) => ({ ...c, sources: c.sources.filter((_, x) => x !== i) }));

  const S = status || {};
  return (
    <div className="fade-in">
      <div className="section-title">24/7 Lead Scraper · OSINT/AI HQ Filter</div>

      <div className="stat-grid" style={{ marginBottom: 22 }}>
        <div className="stat"><div className="label">Engine</div>
          <div className={`value ${S.scheduler_running ? "lime" : ""}`} style={{ fontSize: 26 }}>{S.scheduler_running ? "RUNNING" : "STOPPED"}</div>
          <div className="sub">{S.status === "running" ? "scraping now…" : "idle · every " + (S.interval_min ?? "—") + "m"}</div></div>
        <div className="stat"><div className="label">Found (session)</div><div className="value">{S.found ?? 0}</div><div className="sub">{S.cycles ?? 0} cycles</div></div>
        <div className="stat"><div className="label">Qualified</div><div className="value lime">{S.qualified ?? 0}</div><div className="sub">passed HQ filter</div></div>
        <div className="stat"><div className="label">Total Scraped</div><div className="value cyan">{S.total_scraped_leads ?? 0}</div><div className="sub">in pipeline</div></div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16 }}>
        <div className="panel">
          <div className="panel-head"><h3>Sources & Schedule</h3>
            <button className="btn btn-sm" onClick={trigger} disabled={triggering} data-testid="scraper-trigger">
              {triggering ? <span className="spinner" /> : <><RefreshCw size={13} /> Run Now</>}
            </button>
          </div>
          <div className="panel-body">
            {cfg && (
              <>
                <div className="toolbar" style={{ marginBottom: 16 }}>
                  <label className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>INTERVAL (min)</label>
                  <input className="search-input" style={{ width: 80 }} type="number" value={cfg.interval_min}
                    onChange={(e) => upd("interval_min", parseInt(e.target.value) || 30)} data-testid="scraper-interval" />
                  <label className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>MIN SCORE</label>
                  <input className="search-input" style={{ width: 80 }} type="number" value={cfg.min_score}
                    onChange={(e) => upd("min_score", parseFloat(e.target.value) || 0)} data-testid="scraper-minscore" />
                  <label className="mono" style={{ fontSize: 11, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
                    <input type="checkbox" checked={cfg.use_ai} onChange={(e) => upd("use_ai", e.target.checked)} /> AI FILTER
                  </label>
                  <select className="select" value={cfg.ai_model} onChange={(e) => upd("ai_model", e.target.value)} data-testid="scraper-model">
                    <option value="deepseek">DeepSeek</option>
                    <option value="qwen">Qwen</option>
                  </select>
                  <label className="mono" style={{ fontSize: 11, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
                    <input type="checkbox" checked={cfg.enabled} onChange={(e) => upd("enabled", e.target.checked)} /> ENABLED
                  </label>
                </div>

                {cfg.sources.map((s, i) => (
                  <div key={i} className="toolbar" style={{ marginBottom: 8 }}>
                    <select className="select" value={s.provider} onChange={(e) => updSrc(i, "provider", e.target.value)}>
                      <option value="hackernews">HackerNews</option>
                      <option value="github">GitHub</option>
                      <option value="reddit">Reddit</option>
                    </select>
                    <input className="search-input" style={{ flex: 1 }} placeholder="query" value={s.query}
                      onChange={(e) => updSrc(i, "query", e.target.value)} />
                    {s.provider === "reddit" && (
                      <input className="search-input" style={{ width: 130 }} placeholder="subreddit" value={s.subreddit || ""}
                        onChange={(e) => updSrc(i, "subreddit", e.target.value)} />
                    )}
                    <input className="search-input" style={{ width: 130 }} placeholder="category" value={s.category}
                      onChange={(e) => updSrc(i, "category", e.target.value)} />
                    <button className="icon-btn danger" onClick={() => delSrc(i)}><Trash2 size={13} /></button>
                  </div>
                ))}
                <div className="toolbar" style={{ marginTop: 12 }}>
                  <button className="btn btn-ghost btn-sm" onClick={addSrc} data-testid="scraper-add-source"><Plus size={13} /> Add Source</button>
                  <button className="btn btn-sm" onClick={save} disabled={saving} data-testid="scraper-save">{saving ? <span className="spinner" /> : "Save Config"}</button>
                </div>
                {S.last_error && <p className="mono" style={{ fontSize: 11, color: "var(--amber)", marginTop: 14 }}>⚠ {S.last_error}</p>}
                <p className="mono" style={{ fontSize: 11, color: "var(--muted)", marginTop: 10 }}>
                  next run: {S.next_run ? new Date(S.next_run).toLocaleTimeString() : "—"} · last: {S.last_run ? new Date(S.last_run).toLocaleTimeString() : "never"}
                </p>
              </>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>Live Lead Feed</h3></div>
          <div className="panel-body" style={{ padding: 0, maxHeight: 520, overflowY: "auto" }}>
            {feed.map((l) => (
              <div key={l.id} style={{ padding: "14px 18px", borderBottom: "1px solid var(--line)" }} data-testid={`feed-${l.id}`}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <span className="badge">{l.source_site}</span>
                  <span className={`badge ${scoreClass(l.score)}`}>{Math.round(l.score)}</span>
                </div>
                <div style={{ fontSize: 13, marginTop: 8, color: "var(--txt)", lineHeight: 1.5 }}>{(l.title || l.raw_text || "").slice(0, 120)}…</div>
                <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>{l.full_name} · {l.category}{l.tags === "ai_pending" && <span style={{ color: "var(--amber)" }}> · ai_pending</span>}</div>
              </div>
            ))}
            {!feed.length && <div className="empty"><RefreshCw size={32} /><div>No scraped leads yet — hit Run Now.</div></div>}
          </div>
        </div>
      </div>
    </div>
  );
}
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
