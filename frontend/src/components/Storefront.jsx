import React, { useEffect, useState, useCallback } from "react";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";
import {
  ShieldCheck, AlertTriangle, Lock, MapPin, CreditCard, X, Layers,
  BadgeCheck, Crosshair, RefreshCw,
} from "lucide-react";

const TIER_CLASS = {
  Strategic: "tier-strategic",
  Tactical: "tier-tactical",
  Operational: "tier-operational",
};
const fmtNode = (n) => (n || "").replace(/_/g, " ");
const confColor = (s) => (s >= 80 ? "#ffcf4d" : s >= 60 ? "var(--accent)" : "#5fb6ff");
const catLabel = (c) => (c || "—").replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());

function IntelCard({ lead, picked, onToggle, onAcquire }) {
  const conf = Math.round(lead.data_confidence_score || 0);
  return (
    <div className={`intel-card ${picked ? "picked" : ""}`} data-testid={`intel-card-${lead.id}`}>
      <div className="intel-top">
        <div>
          <span className={`tier-badge ${TIER_CLASS[lead.operational_value_tier] || "tier-operational"}`}
            data-testid={`intel-tier-${lead.id}`}>
            {lead.operational_value_tier || "Operational"}
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
        <div className="conf-num" style={{ color: confColor(conf) }} data-testid={`intel-confidence-${lead.id}`}>
          {conf}<small>/100</small>
        </div>
        <div className="conf-meta">
          <div className="conf-label">Data Confidence Score</div>
          <div className="conf-bar"><i style={{ width: `${Math.min(conf, 100)}%` }} /></div>
        </div>
      </div>

      {lead.ai_summary && (
        <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.5 }}>{lead.ai_summary}</div>
      )}

      <div>
        <div className="sf-section-label"><BadgeCheck size={11} style={{ verticalAlign: -2 }} /> Cross-Verification</div>
        <div className="node-row">
          {(lead.cross_verification || []).length
            ? lead.cross_verification.map((n) => (
              <span key={n} className="node-chip"><ShieldCheck size={11} />{fmtNode(n)}</span>
            ))
            : <span className="muted" style={{ fontSize: 11 }}>No nodes verified</span>}
        </div>
      </div>

      {(lead.risk_matrix || []).length > 0 && (
        <div>
          <div className="sf-section-label"><AlertTriangle size={11} style={{ verticalAlign: -2 }} /> Threat / Risk Matrix</div>
          <div className="risk-row">
            {lead.risk_matrix.map((r, i) => (
              <span key={i} className={`risk-chip risk-${r.severity || "low"}`}>
                <AlertTriangle size={10} />{fmtNode(r.flag)}
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
  const [data, setData] = useState({ leads: [], total: 0, filters: { industries: [], states: [], tiers: [] } });
  const [f, setF] = useState({ industry: "", state: "", tier: "", min_confidence: 0 });
  const [picked, setPicked] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [result, setResult] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    const p = new URLSearchParams();
    if (f.industry) p.set("industry", f.industry);
    if (f.state) p.set("state", f.state);
    if (f.tier) p.set("tier", f.tier);
    if (f.min_confidence) p.set("min_confidence", f.min_confidence);
    api.get(`/storefront/leads?${p.toString()}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
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
        <span className="mono" style={{ fontSize: 12, color: "var(--accent)" }}>
          <CreditCard size={13} style={{ verticalAlign: -2, marginRight: 6 }} />{user?.credits ?? 0} credits
        </span>
      </div>

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
            {purchasing ? <span className="spinner" /> : `Acquire ${pickedList.length} Package${pickedList.length === 1 ? "" : "s"}`}
          </button>
        </div>
      )}

      {result && <ResultModal result={result} onClose={() => setResult(null)} />}
    </div>
  );
}
