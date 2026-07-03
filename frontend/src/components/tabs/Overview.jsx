import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { cat, scoreClass } from "../helpers";

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
