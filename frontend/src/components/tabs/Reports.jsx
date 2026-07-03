import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { RefreshCw } from "lucide-react";

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
