import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { Users, Building2, ScrollText, Activity, Inbox, Mail, ShieldAlert } from "lucide-react";
import { MonitorPanel, TenantsPanel, AuditPanel, OutreachPanel, PilotLeadsPanel } from "./AdminPanels";

const GOV_ROLES = ["user", "analyst", "tenant_admin", "admin", "owner"];

export function Admin() {
  const [section, setSection] = useState("operators");
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const load = () => api.get("/admin/users").then((r) => setUsers(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message));
  useEffect(() => { if (section === "operators") load(); }, [section]);
  const setRole = async (id, role) => { await api.patch(`/admin/users/${id}/role`, { role }); load(); };

  const SECTIONS = [
    { id: "operators", label: "Operators", icon: Users },
    { id: "tenants", label: "Tenants", icon: Building2 },
    { id: "audit", label: "Audit Trail", icon: ScrollText },
    { id: "monitoring", label: "Monitoring", icon: Activity },
    { id: "pilot", label: "Pilot Leads", icon: Inbox },
    { id: "outreach", label: "Outreach", icon: Mail },
  ];

  return (
    <div className="fade-in">
      <div className="section-title">Governance Console</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {SECTIONS.map((s) => {
          const Ico = s.icon;
          return (
            <button key={s.id} className={`status-pill ${section === s.id ? "active" : ""}`}
              style={{ cursor: "pointer", borderColor: section === s.id ? "var(--accent)" : undefined, color: section === s.id ? "var(--accent)" : undefined }}
              onClick={() => setSection(s.id)} data-testid={`gov-tab-${s.id}`}>
              <Ico size={13} style={{ marginRight: 6, verticalAlign: -2 }} />{s.label}
            </button>
          );
        })}
      </div>

      {section === "operators" && (err ? <div className="empty"><ShieldAlert size={36} /><div>{err}</div></div> : (
        <div className="panel" data-testid="gov-operators">
          <div className="panel-head"><h3><Users size={15} style={{ verticalAlign: -2, marginRight: 8 }} />All Operators ({users.length})</h3></div>
          <div className="panel-body" style={{ padding: 0 }}>
            <table className="tbl">
              <thead><tr><th>Operator</th><th>Email</th><th>Tenant</th><th>Role</th><th>Credits</th><th>Assign role</th></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} data-testid={`admin-user-${u.id}`}>
                    <td className="name">{u.name}</td>
                    <td className="muted">{u.email}</td>
                    <td className="muted">{u.tenant_name || u.tenant_id}</td>
                    <td><span className={`badge ${["admin", "owner"].includes(u.role) ? "hot" : ""}`}>{u.role}</span></td>
                    <td>{u.credits ?? 0}</td>
                    <td>
                      <select className="select" value={u.role} onChange={(e) => setRole(u.id, e.target.value)} data-testid={`admin-role-${u.id}`}>
                        {GOV_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      {section === "tenants" && <TenantsPanel />}
      {section === "audit" && <AuditPanel />}
      {section === "monitoring" && <MonitorPanel />}
      {section === "pilot" && <PilotLeadsPanel />}
      {section === "outreach" && <OutreachPanel />}
    </div>
  );
}
