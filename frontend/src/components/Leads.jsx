import React, { useEffect, useState, useCallback } from "react";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { cat, scoreClass } from "./helpers";
import {
  Search, Download, Sparkles, Lock, Unlock, DollarSign, Trash2, CreditCard,
} from "lucide-react";

/* ---- filter + bulk-action toolbar ---- */
function LeadsToolbar({ search, setSearch, category, setCategory, load, exportCsv, enrichAll, enriching }) {
  return (
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
  );
}

/* ---- single lead row ---- */
function LeadRow({ lead, onUnlock, onBuy, onSell, onDelete }) {
  const l = lead;
  return (
    <tr data-testid={`lead-row-${l.id}`}>
      <td className="name">{l.full_name || l.company || "—"}<div className="muted">{l.city}{l.state ? ", " + l.state : ""}</div></td>
      <td className="muted">
        {l.locked
          ? <span style={{ color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 12 }}><Lock size={12} style={{ verticalAlign: -1, marginRight: 5 }} />locked</span>
          : <>{l.email || "—"}<div>{l.phone}</div></>}
      </td>
      <td><span className="badge">{cat(l.category)}</span></td>
      <td>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className={`badge ${scoreClass(l.score)}`}>{Math.round(l.score)}</span>
          <div className="score-bar"><i style={{ width: `${Math.min(l.score, 100)}%` }} /></div>
        </div>
      </td>
      <td className="muted" style={{ maxWidth: 260, fontSize: 13 }}>
        {l.ai_summary || <span style={{ opacity: .5 }}>not enriched</span>}
        {l.ai_budget_est && <div style={{ color: "var(--accent)", marginTop: 4 }}>{l.ai_budget_est}</div>}
      </td>
      <td><span className={`badge ${l.is_sold ? "sold" : ""}`}>{l.status}</span></td>
      <td>
        <div className="row-actions">
          {l.locked && <button className="icon-btn" style={{ color: "var(--accent)", borderColor: "var(--accent-dim)" }} title="Unlock (1 credit)" onClick={() => onUnlock(l.id)} data-testid={`lead-unlock-${l.id}`}><Unlock size={14} /></button>}
          {l.locked && <button className="btn btn-sm" style={{ padding: "4px 10px", fontSize: 12 }} title={`Buy this lead for $${l.price}`} onClick={() => onBuy(l.id)} data-testid={`lead-buy-${l.id}`}><CreditCard size={13} style={{ verticalAlign: -2, marginRight: 4 }} />${l.price}</button>}
          <button className="icon-btn" title="Mark sold" onClick={() => onSell(l.id)} data-testid={`lead-sell-${l.id}`}><DollarSign size={14} /></button>
          <button className="icon-btn danger" title="Delete" onClick={() => onDelete(l.id)} data-testid={`lead-del-${l.id}`}><Trash2 size={14} /></button>
        </div>
      </td>
    </tr>
  );
}

/* ---- orchestrator ---- */
export function Leads() {
  const { user, refreshUser } = useAuth();
  const [data, setData] = useState({ leads: [], total: 0 });
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [enriching, setEnriching] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    const p = new URLSearchParams();
    if (search) p.set("search", search);
    if (category) p.set("category", category);
    api.get(`/leads?${p.toString()}`).then((r) => setData(r.data)).finally(() => setLoading(false));
  }, [search, category]);

  useEffect(() => { load(); }, [category, load]);

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
      if (e.response?.status === 402) {
        if (window.confirm("Out of credits. Go to Billing to buy a pack?")) window.dispatchEvent(new CustomEvent("nexus-goto", { detail: "billing" }));
      } else alert(e.response?.data?.detail || e.message);
    }
  };
  const del = async (id) => { if (window.confirm("Delete this lead?")) { await api.delete(`/leads/${id}`); load(); } };
  const buy = async (id) => {
    try {
      const r = await api.post(`/leads/${id}/buy`, { origin_url: window.location.origin });
      window.location.href = r.data.url;
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };
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
        <LeadsToolbar search={search} setSearch={setSearch} category={category} setCategory={setCategory}
          load={load} exportCsv={exportCsv} enrichAll={enrichAll} enriching={enriching} />
        <div className="panel-body" style={{ padding: 0, overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr>
              <th>Lead</th><th>Contact</th><th>Category</th><th>Score</th><th>AI Summary</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
              {loading
                ? <tr><td colSpan={7} style={{ padding: 30, textAlign: "center" }}><span className="spinner lime" /></td></tr>
                : data.leads.map((l) => (
                  <LeadRow key={l.id} lead={l} onUnlock={unlock} onBuy={buy} onSell={sell} onDelete={del} />
                ))}
              {!loading && !data.leads.length && <tr><td colSpan={7} className="empty">No leads match your filters.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
