import React, { useEffect, useState, useCallback } from "react";
import api from "../lib/api";
import { toast } from "./ui/sonner";
import { useAuth } from "../context/AuthContext";
import {
  ShieldCheck, AlertTriangle, Lock, MapPin, CreditCard, X, Layers,
  BadgeCheck, Crosshair, RefreshCw, FileText, Send, Triangle, Square, Circle, ShieldAlert,
  Radar, Sparkles,
} from "lucide-react";

const TIER_CLASS = { Strategic: "tier-strategic", Tactical: "tier-tactical", Operational: "tier-operational" };
const TIER_ICON = { Strategic: Triangle, Tactical: Square, Operational: Circle };
const NODE_LABEL = {
  Email_Syntax_Valid: "Email Valid", Domain_MX_Match: "MX Match",
  Public_Registry_Verified: "Registry Verified", Social_Footprint_Consistent: "Footprint Consistent",
  Phone_Format_Valid: "Phone Valid", Geo_Located: "Geo Located",
};
const nodeLabel = (n) => NODE_LABEL[n] || (n || "").replace(/_/g, " ");
const fmtFlag = (n) => (n || "").replace(/_/g, " ");
const confColor = (s) => (s >= 80 ? "#ffcf4d" : s >= 60 ? "var(--accent)" : "#5fb6ff");
const catLabel = (c) => (c || "—").replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());

const threatLevel = (risk) => {
  if (!risk || !risk.length) return { label: "Nominal", lvl: "low" };
  if (risk.some((r) => r.severity === "high")) return { label: "Elevated", lvl: "high" };
  if (risk.some((r) => r.severity === "medium")) return { label: "Guarded", lvl: "medium" };
  return { label: "Low", lvl: "low" };
};

function IntelCard({ lead, picked, onToggle, onAcquire }) {
  const conf = Math.round(lead.data_confidence_score || 0);
  const tier = lead.operational_value_tier || "Operational";
  const TierIco = TIER_ICON[tier] || Circle;
  const threat = threatLevel(lead.risk_matrix);
  return (
    <div className={`intel-card ${picked ? "picked" : ""}`} data-testid={`intel-card-${lead.id}`}>
      <div className="intel-top">
        <div>
          <span className={`tier-badge ${TIER_CLASS[tier]}`} data-testid={`intel-tier-${lead.id}`}>
            <TierIco size={10} className="tier-ico" />{tier}
          </span>
          <div className="sf-section-label" style={{ marginTop: 8 }}>{catLabel(lead.category)}</div>
        </div>
        <label className="status-pill" style={{ cursor: "pointer", gap: 6 }}>
          <input type="checkbox" checked={picked} onChange={() => onToggle(lead.id)}
            data-testid={`intel-select-${lead.id}`} style={{ accentColor: "var(--accent)" }} />
          SELECT
        </label>
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 15 }} data-testid={`intel-entity-${lead.id}`}>
          <Lock size={12} style={{ verticalAlign: -1, marginRight: 6, color: "var(--muted)" }} />
          {lead.company_masked || "Verified Entity"}
        </div>
        <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>
          <MapPin size={11} style={{ verticalAlign: -1, marginRight: 4 }} />
          {[lead.city, lead.state].filter(Boolean).join(", ") || "Undisclosed"} · {lead.contact_masked || "contact sealed"}
        </div>
      </div>

      <div className="conf-block">
        <div className="conf-num acc-num" style={{ color: confColor(conf) }} data-testid={`intel-confidence-${lead.id}`}>
          {conf}<small>%</small>
        </div>
        <div className="conf-meta">
          <div className="conf-label">AI Analyst · Accuracy Vector</div>
          <div className="conf-bar"><i style={{ width: `${Math.min(conf, 100)}%` }} /></div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span className={`risk-pill lvl-${threat.lvl}`} data-testid={`intel-threat-${lead.id}`}>
          <ShieldAlert size={11} /> Threat: {threat.label}
        </span>
        {lead.ai_budget_est && <span className="muted mono" style={{ fontSize: 11 }}>{lead.ai_budget_est}</span>}
      </div>

      {lead.ai_summary && (
        <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.5 }}>{lead.ai_summary}</div>
      )}

      <div>
        <div className="sf-section-label"><BadgeCheck size={11} style={{ verticalAlign: -2 }} /> Verification Nodes</div>
        <div className="node-row">
          {(lead.cross_verification || []).length
            ? lead.cross_verification.map((n) => (
              <span key={n} className="node-chip"><ShieldCheck size={11} />{nodeLabel(n)}</span>
            ))
            : <span className="muted" style={{ fontSize: 11 }}>No nodes verified</span>}
        </div>
      </div>

      {(lead.risk_matrix || []).length > 0 && (
        <div>
          <div className="sf-section-label"><AlertTriangle size={11} style={{ verticalAlign: -2 }} /> Risk Matrix</div>
          <div className="risk-row">
            {lead.risk_matrix.map((r, i) => (
              <span key={r.flag || i} className={`risk-chip risk-${r.severity || "low"}`}>
                <AlertTriangle size={10} />{fmtFlag(r.flag)}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="intel-foot">
        <span className="intel-price"><CreditCard size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
          {lead.price_per_lead} {lead.price_per_lead === 1 ? "credit" : "credits"}</span>
        <button className="btn btn-sm" onClick={() => onAcquire(lead.id)} data-testid={`intel-acquire-${lead.id}`}>
          Acquire Intel
        </button>
      </div>
    </div>
  );
}

function BundleStrip({ bundles, active, onPick }) {
  if (!bundles || !bundles.length) return null;
  return (
    <div className="bundle-strip" data-testid="bundle-strip">
      {bundles.map((b) => (
        <div key={b.industry} className={`bundle-card ${active === b.industry ? "active" : ""}`}
          onClick={() => onPick(active === b.industry ? "" : b.industry)} data-testid={`bundle-${b.industry}`}>
          <div className="bc-count">{b.count}</div>
          <div className="bc-name">{catLabel(b.industry)}</div>
          <div className="bc-meta">~{b.avg_confidence}% acc · from {b.from_price} cr{b.strategic ? ` · ${b.strategic}◭` : ""}</div>
        </div>
      ))}
    </div>
  );
}

const RFP_EMPTY = {
  agency_name: "", contact_name: "", email: "", regions: "", sectors: "",
  budget: "", timeline: "", classification: "Unclassified", scope: "",
};

function RFPModal({ onClose }) {
  const [form, setForm] = useState(RFP_EMPTY);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const r = await api.post("/storefront/rfp", form);
      setDone(r.data);
    } catch (e2) { setErr(e2.response?.data?.detail || e2.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="sf-modal-wrap" data-testid="rfp-modal">
      <div className="sf-modal fade-in" style={{ maxWidth: 680 }}>
        <div className="rfp-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ fontSize: 18 }}>
              <FileText size={18} style={{ verticalAlign: -3, marginRight: 8, color: "var(--accent)" }} />
              Request Agency Scope / Submit RFP
            </h2>
            <div className="rfp-trust"><Lock size={11} /> Secure Enclave · AES-256 · Procurement Desk</div>
          </div>
          <button className="icon-btn" onClick={onClose} data-testid="rfp-close"><X size={16} /></button>
        </div>

        {done ? (
          <div className="rfp-ok" data-testid="rfp-success">
            <ShieldCheck size={42} style={{ color: "var(--accent)" }} />
            <h3 style={{ marginTop: 14 }}>Scope Request Logged</h3>
            <div className="muted" style={{ marginTop: 8, fontSize: 13 }}>{done.message}</div>
            <div className="mono" style={{ marginTop: 10, fontSize: 11 }}>REF: {done.id}</div>
            <button className="btn" style={{ marginTop: 20 }} onClick={onClose} data-testid="rfp-done-btn">Close</button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <div className="rfp-grid">
              <div className="rfp-field">
                <label>Agency / Organization</label>
                <input className="input" required value={form.agency_name} onChange={set("agency_name")}
                  placeholder="e.g. Dept. of Public Safety" data-testid="rfp-agency-input" />
              </div>
              <div className="rfp-field">
                <label>Contact Officer</label>
                <input className="input" required value={form.contact_name} onChange={set("contact_name")}
                  placeholder="Full name" data-testid="rfp-contact-input" />
              </div>
              <div className="rfp-field">
                <label>Official Email</label>
                <input className="input" type="email" required value={form.email} onChange={set("email")}
                  placeholder="officer@agency.gov" data-testid="rfp-email-input" />
              </div>
              <div className="rfp-field">
                <label>Classification</label>
                <select className="select" value={form.classification} onChange={set("classification")} data-testid="rfp-classification-select">
                  <option>Unclassified</option>
                  <option>Controlled / CUI</option>
                  <option>Confidential</option>
                  <option>Secret</option>
                </select>
              </div>
              <div className="rfp-field">
                <label>Target Regions</label>
                <input className="input" value={form.regions} onChange={set("regions")}
                  placeholder="e.g. Tampa Bay, FL Gulf Coast" data-testid="rfp-regions-input" />
              </div>
              <div className="rfp-field">
                <label>Target Sectors</label>
                <input className="input" value={form.sectors} onChange={set("sectors")}
                  placeholder="e.g. critical infra, logistics" data-testid="rfp-sectors-input" />
              </div>
              <div className="rfp-field">
                <label>Budget Envelope</label>
                <input className="input" value={form.budget} onChange={set("budget")}
                  placeholder="e.g. $50k–$250k" data-testid="rfp-budget-input" />
              </div>
              <div className="rfp-field">
                <label>Timeline</label>
                <input className="input" value={form.timeline} onChange={set("timeline")}
                  placeholder="e.g. Q3 FY26" data-testid="rfp-timeline-input" />
              </div>
              <div className="rfp-field full">
                <label>Intelligence Parameters / Scope</label>
                <textarea className="input" value={form.scope} onChange={set("scope")}
                  placeholder="Describe the custom intelligence parameters, data fields, verification depth, and delivery cadence required."
                  data-testid="rfp-scope-input" />
              </div>
            </div>
            {err && <div className="err-box" style={{ marginTop: 14 }} data-testid="rfp-error">{err}</div>}
            <button className="btn" type="submit" disabled={busy} style={{ width: "100%", marginTop: 18 }} data-testid="rfp-submit">
              {busy ? <span className="spinner" /> : <><Send size={14} style={{ verticalAlign: -2, marginRight: 8 }} />Transmit Secure Request</>}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function GenerateModal({ onClose, onDone }) {
  const COUNTIES = ["Hillsborough County", "Pinellas County", "Manatee County", "Pasco County", "Hernando County"];
  const [sectors, setSectors] = useState([]);
  const [form, setForm] = useState({ sector: "financial_services", county: "Hillsborough County", limit: 100, ai_enrich: true });
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => { api.get("/storefront/sectors").then((r) => setSectors(r.data.sectors || [])).catch(() => {}); }, []);

  const trackEnrichment = useCallback((jobId, total, sector) => {
    const tid = `enrich-${jobId}`;
    const label = (sector || "").replace(/_/g, " ");
    toast.loading(`Enriching ${label} leads · 0/${total}`, {
      id: tid, description: "AI analyst + OSINT verification running…", duration: Infinity,
    });
    const poll = setInterval(async () => {
      try {
        const { data } = await api.get(`/storefront/generate-status/${jobId}`);
        if (data.status === "complete") {
          clearInterval(poll);
          toast.success(`Enrichment complete · ${data.done}/${data.total} ${label} leads`, {
            id: tid, description: "Marketplace updated with verified intel.", duration: 6000,
          });
          onDone && onDone();
        } else {
          toast.loading(`Enriching ${label} leads · ${data.done}/${data.total}`, {
            id: tid, description: "AI analyst + OSINT verification running…", duration: Infinity,
          });
        }
      } catch (err) {
        clearInterval(poll);
        toast.error("Enrichment tracking lost", { id: tid, description: "Leads were still saved.", duration: 5000 });
      }
    }, 2000);
  }, [onDone]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const r = await api.post("/storefront/generate-leads", form);
      setRes(r.data);
      onDone && onDone();
      if (r.data.job_id && r.data.enrich_total > 0) {
        trackEnrichment(r.data.job_id, r.data.enrich_total, r.data.sector);
      }
    } catch (e2) { setErr(e2.response?.data?.detail || e2.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="sf-modal-wrap" data-testid="generate-modal">
      <div className="sf-modal fade-in" style={{ maxWidth: 520 }}>
        <div className="rfp-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ fontSize: 18 }}>
              <Radar size={18} style={{ verticalAlign: -3, marginRight: 8, color: "var(--accent)" }} />
              Generate Intel (Live OSM Harvest)
            </h2>
            <div className="rfp-trust"><Sparkles size={11} /> OpenStreetMap · OSINT verified · AI enriched</div>
          </div>
          <button className="icon-btn" onClick={onClose} data-testid="generate-close"><X size={16} /></button>
        </div>

        {res ? (
          <div className="rfp-ok" data-testid="generate-success">
            <ShieldCheck size={42} style={{ color: "var(--accent)" }} />
            <h3 style={{ marginTop: 14 }}>{res.new} new · {res.generated} harvested</h3>
            <div className="muted" style={{ marginTop: 8, fontSize: 13 }}>{res.message}</div>
            <button className="btn" style={{ marginTop: 20 }} onClick={onClose} data-testid="generate-done-btn">View Marketplace</button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <div className="rfp-field" style={{ marginBottom: 14 }}>
              <label>Sector</label>
              <select className="select" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} data-testid="generate-sector">
                {(sectors.length ? sectors : ["real_estate"]).map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase())}</option>
                ))}
              </select>
            </div>
            <div className="rfp-field" style={{ marginBottom: 14 }}>
              <label>County</label>
              <select className="select" value={form.county} onChange={(e) => setForm({ ...form, county: e.target.value })} data-testid="generate-county">
                {COUNTIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="rfp-field" style={{ marginBottom: 14 }}>
              <label>Max records</label>
              <input className="input" type="number" min="1" max="300" value={form.limit}
                onChange={(e) => setForm({ ...form, limit: Number(e.target.value) })} data-testid="generate-limit" />
            </div>
            <label className="muted" style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={form.ai_enrich} onChange={(e) => setForm({ ...form, ai_enrich: e.target.checked })}
                style={{ accentColor: "var(--accent)" }} data-testid="generate-aienrich" />
              Run deep AI enrichment (background)
            </label>
            {err && <div className="err-box" style={{ marginTop: 14 }} data-testid="generate-error">{err}</div>}
            <button className="btn" type="submit" disabled={busy} style={{ width: "100%", marginTop: 18 }} data-testid="generate-submit">
              {busy ? <span className="spinner" /> : <><Radar size={14} style={{ verticalAlign: -2, marginRight: 8 }} />Harvest Live Leads</>}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function ResultModal({ result, onClose }) {
  return (
    <div className="sf-modal-wrap" data-testid="storefront-result-modal">
      <div className="sf-modal fade-in">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <h2 style={{ fontSize: 18 }}>
            <ShieldCheck size={18} style={{ verticalAlign: -3, marginRight: 8, color: "var(--accent)" }} />
            {result.purchased} Intel Package{result.purchased === 1 ? "" : "s"} Acquired
          </h2>
          <button className="icon-btn" onClick={onClose} data-testid="storefront-result-close"><X size={16} /></button>
        </div>
        <div className="muted mono" style={{ fontSize: 12, marginBottom: 16 }}>
          Charged {result.charged_credits} credits · {result.credits_remaining} credits remaining
        </div>
        {(result.leads || []).map((l) => (
          <div key={l.id} className="sf-unlocked-row" data-testid={`unlocked-lead-${l.id}`}>
            <div style={{ fontWeight: 700 }}>{l.company || l.full_name || "Entity"} · <span className="muted" style={{ fontWeight: 400 }}>{[l.city, l.state].filter(Boolean).join(", ")}</span></div>
            <div className="mono" style={{ fontSize: 13, marginTop: 6 }}>{l.email || "—"}</div>
            <div className="mono" style={{ fontSize: 13 }}>{l.phone || "—"}</div>
            {l.website && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{l.website}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

export function Storefront() {
  const { user, refreshUser } = useAuth();
  const [data, setData] = useState({ leads: [], total: 0, bundles: [], filters: { industries: [], states: [], tiers: [] } });
  const [f, setF] = useState({ industry: "", state: "", tier: "", min_confidence: 0 });
  const [picked, setPicked] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [result, setResult] = useState(null);
  const [rfpOpen, setRfpOpen] = useState(false);
  const [genOpen, setGenOpen] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const p = new URLSearchParams();
    if (f.industry) p.set("industry", f.industry);
    if (f.state) p.set("state", f.state);
    if (f.tier) p.set("tier", f.tier);
    if (f.min_confidence) p.set("min_confidence", f.min_confidence);
    api.get(`/storefront/leads?${p.toString()}`).then((r) => setData(r.data)).finally(() => setLoading(false));
  }, [f]);

  useEffect(() => { load(); }, [load]);

  const toggle = (id) => setPicked((s) => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n;
  });

  const buy = async (ids) => {
    if (!ids.length) return;
    setPurchasing(true);
    try {
      const r = await api.post("/storefront/purchase-leads", { lead_ids: ids });
      setResult(r.data);
      setPicked(new Set());
      await refreshUser();
      load();
    } catch (e) {
      if (e.response?.status === 402) {
        if (window.confirm((e.response?.data?.detail || "Insufficient credits") + "\n\nGo to Billing to buy credits?"))
          window.dispatchEvent(new CustomEvent("nexus-goto", { detail: "billing" }));
      } else alert(e.response?.data?.detail || e.message);
    } finally { setPurchasing(false); }
  };

  const filt = data.filters || { industries: [], states: [], tiers: [] };
  const pickedList = [...picked];
  const pickedCost = data.leads.filter((l) => picked.has(l.id)).reduce((s, l) => s + (l.price_per_lead || 0), 0);

  return (
    <div className="fade-in" data-testid="storefront-root">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span><Crosshair size={15} style={{ verticalAlign: -2, marginRight: 8 }} />
          Intelligence Marketplace · {data.total} verified packages</span>
        <div className="sf-actions">
          <span className="mono" style={{ fontSize: 12, color: "var(--accent)" }}>
            <CreditCard size={13} style={{ verticalAlign: -2, marginRight: 6 }} />{user?.credits ?? 0} credits
          </span>
          <button className="rfp-open-btn" onClick={() => setRfpOpen(true)} data-testid="rfp-open-btn">
            <FileText size={13} /> Request Agency Scope
          </button>
          {user?.role === "admin" && (
            <button className="rfp-open-btn" onClick={() => setGenOpen(true)} data-testid="generate-open-btn">
              <Radar size={13} /> Generate Leads
            </button>
          )}
        </div>
      </div>

      <BundleStrip bundles={data.bundles} active={f.industry} onPick={(ind) => setF({ ...f, industry: ind })} />

      <div className="sf-filters">
        <select className="select" value={f.industry} onChange={(e) => setF({ ...f, industry: e.target.value })} data-testid="storefront-industry-filter">
          <option value="">All sectors</option>
          {filt.industries.map((i) => <option key={i} value={i}>{catLabel(i)}</option>)}
        </select>
        <select className="select" value={f.state} onChange={(e) => setF({ ...f, state: e.target.value })} data-testid="storefront-state-filter">
          <option value="">All states</option>
          {filt.states.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="select" value={f.tier} onChange={(e) => setF({ ...f, tier: e.target.value })} data-testid="storefront-tier-filter">
          <option value="">All tiers</option>
          {(filt.tiers || []).map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <div className="sf-conf">
          <span>MIN CONFIDENCE</span>
          <input type="range" min="0" max="100" step="5" value={f.min_confidence}
            onChange={(e) => setF({ ...f, min_confidence: Number(e.target.value) })}
            data-testid="storefront-confidence-filter" style={{ accentColor: "var(--accent)" }} />
          <b style={{ color: "var(--accent)" }}>{f.min_confidence}</b>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} data-testid="storefront-refresh"><RefreshCw size={13} /></button>
      </div>

      {loading
        ? <div style={{ padding: 50, textAlign: "center" }}><span className="spinner lime" /></div>
        : data.leads.length
          ? <div className="intel-grid">
            {data.leads.map((l) => (
              <IntelCard key={l.id} lead={l} picked={picked.has(l.id)} onToggle={toggle} onAcquire={(id) => buy([id])} />
            ))}
          </div>
          : <div className="panel"><div className="empty" style={{ padding: 40 }}>No verified intel packages match your filters.</div></div>}

      {pickedList.length > 0 && (
        <div className="sf-cart-bar" data-testid="storefront-cart-bar">
          <span className="mono" style={{ fontSize: 13 }}>
            <Layers size={14} style={{ verticalAlign: -3, marginRight: 8, color: "var(--accent)" }} />
            {pickedList.length} selected · <b style={{ color: "var(--accent)" }}>{pickedCost} credits</b>
          </span>
          <button className="btn" onClick={() => buy(pickedList)} disabled={purchasing} data-testid="storefront-bulk-acquire">
            {purchasing ? <span className="spinner" /> : `Atomic Purchase · ${pickedList.length} Package${pickedList.length === 1 ? "" : "s"}`}
          </button>
        </div>
      )}

      {rfpOpen && <RFPModal onClose={() => setRfpOpen(false)} />}
      {genOpen && <GenerateModal onClose={() => { setGenOpen(false); load(); }} onDone={load} />}
      {result && <ResultModal result={result} onClose={() => setResult(null)} />}
    </div>
  );
}
