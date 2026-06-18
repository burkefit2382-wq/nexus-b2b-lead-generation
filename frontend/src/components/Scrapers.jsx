import React, { useEffect, useState, useCallback } from "react";
import api from "../lib/api";
import { scoreClass, nextUid } from "./helpers";
import { RefreshCw, Plus, Trash2 } from "lucide-react";

/* ---- status cards ---- */
function ScraperStatsCards({ S }) {
  const cards = [
    { label: "Engine", value: S.scheduler_running ? "RUNNING" : "STOPPED",
      cls: S.scheduler_running ? "lime" : "", size: 26,
      sub: S.status === "running" ? "scraping now…" : `idle · every ${S.interval_min ?? "—"}m` },
    { label: "Found (session)", value: S.found ?? 0, cls: "", sub: `${S.cycles ?? 0} cycles` },
    { label: "Qualified", value: S.qualified ?? 0, cls: "lime", sub: "passed HQ filter" },
    { label: "Total Scraped", value: S.total_scraped_leads ?? 0, cls: "cyan", sub: "in pipeline" },
  ];
  return (
    <div className="stat-grid" style={{ marginBottom: 22 }}>
      {cards.map((c) => (
        <div className="stat" key={c.label}>
          <div className="label">{c.label}</div>
          <div className={`value ${c.cls}`} style={c.size ? { fontSize: c.size } : undefined}>{c.value}</div>
          <div className="sub">{c.sub}</div>
        </div>
      ))}
    </div>
  );
}

/* ---- single editable source row ---- */
function SourceRow({ src, onChange, onRemove }) {
  return (
    <div className="toolbar" style={{ marginBottom: 8 }}>
      <select className="select" value={src.provider} onChange={(e) => onChange("provider", e.target.value)}>
        <option value="hackernews">HackerNews</option>
        <option value="github">GitHub</option>
        <option value="reddit">Reddit</option>
      </select>
      <input className="search-input" style={{ flex: 1 }} placeholder="query" value={src.query}
        onChange={(e) => onChange("query", e.target.value)} />
      {src.provider === "reddit" && (
        <input className="search-input" style={{ width: 130 }} placeholder="subreddit" value={src.subreddit || ""}
          onChange={(e) => onChange("subreddit", e.target.value)} />
      )}
      <input className="search-input" style={{ width: 130 }} placeholder="category" value={src.category}
        onChange={(e) => onChange("category", e.target.value)} />
      <button className="icon-btn danger" onClick={onRemove}><Trash2 size={13} /></button>
    </div>
  );
}

/* ---- config + schedule panel ---- */
function ScraperConfigPanel({ cfg, setCfg, S, trigger, triggering, save, saving }) {
  const upd = (k, v) => setCfg((c) => ({ ...c, [k]: v }));
  const updSrc = (uid, k, v) => setCfg((c) => ({
    ...c, sources: c.sources.map((s) => (s._uid === uid ? { ...s, [k]: v } : s)) }));
  const addSrc = () => setCfg((c) => ({
    ...c, sources: [...c.sources, { _uid: nextUid(), provider: "hackernews", query: "", subreddit: "", category: "services" }] }));
  const delSrc = (uid) => setCfg((c) => ({ ...c, sources: c.sources.filter((s) => s._uid !== uid) }));

  return (
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
                onChange={(e) => upd("interval_min", parseInt(e.target.value, 10) || 30)} data-testid="scraper-interval" />
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

            {cfg.sources.map((s) => (
              <SourceRow key={s._uid} src={s}
                onChange={(k, v) => updSrc(s._uid, k, v)} onRemove={() => delSrc(s._uid)} />
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
  );
}

/* ---- live feed panel ---- */
function LiveFeed({ feed }) {
  return (
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
  );
}

/* ---- orchestrator ---- */
export function Scrapers() {
  const [status, setStatus] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [feed, setFeed] = useState([]);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const loadStatus = useCallback(() => api.get("/scraper/status").then((r) => setStatus(r.data)).catch(() => {}), []);
  const loadFeed = useCallback(() => api.get("/scraper/feed?limit=12").then((r) => setFeed(r.data)).catch(() => {}), []);
  const loadCfg = useCallback(() => api.get("/scraper/config")
    .then((r) => setCfg({ ...r.data, sources: (r.data.sources || []).map((s) => ({ ...s, _uid: nextUid() })) }))
    .catch(() => {}), []);

  useEffect(() => {
    loadStatus(); loadCfg(); loadFeed();
    const t = setInterval(() => { loadStatus(); loadFeed(); }, 8000);
    return () => clearInterval(t);
  }, [loadStatus, loadCfg, loadFeed]);

  const trigger = async () => {
    setTriggering(true);
    try { await api.post("/scraper/trigger"); setTimeout(() => { loadStatus(); loadFeed(); }, 6000); }
    finally { setTimeout(() => setTriggering(false), 6000); }
  };
  const save = async () => {
    setSaving(true);
    try {
      const payload = { ...cfg, sources: cfg.sources.map(({ _uid, ...s }) => s) };
      await api.put("/scraper/config", payload);
      loadStatus();
    } catch (e) { alert("Save failed: " + (e.response?.data?.detail || e.message)); }
    finally { setSaving(false); }
  };

  const S = status || {};
  return (
    <div className="fade-in">
      <div className="section-title">24/7 Lead Scraper · OSINT/AI HQ Filter</div>
      <ScraperStatsCards S={S} />
      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16 }}>
        <ScraperConfigPanel cfg={cfg} setCfg={setCfg} S={S} trigger={trigger}
          triggering={triggering} save={save} saving={saving} />
        <LiveFeed feed={feed} />
      </div>
    </div>
  );
}
