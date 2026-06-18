import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Overview, Leads, Osint, AIChat, ApiKeys, Reports, Admin } from "./tabs";
import {
  LayoutGrid, Crosshair, Users2, Bot, KeyRound, ScrollText, ShieldCheck, LogOut
} from "lucide-react";

const NAV = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "leads", label: "Lead Engine", icon: Users2 },
  { id: "osint", label: "OSINT Tools", icon: Crosshair, tag: "12" },
  { id: "ai", label: "NEXUS AI", icon: Bot },
  { id: "reports", label: "Intel Reports", icon: ScrollText },
  { id: "keys", label: "API Keys", icon: KeyRound },
];

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [tab, setTab] = useState("overview");
  const nav = [...NAV, ...(user.role === "admin" ? [{ id: "admin", label: "Admin", icon: ShieldCheck }] : [])];
  const current = nav.find((n) => n.id === tab) || nav[0];

  const render = () => {
    switch (tab) {
      case "leads": return <Leads />;
      case "osint": return <Osint />;
      case "ai": return <AIChat />;
      case "reports": return <Reports />;
      case "keys": return <ApiKeys />;
      case "admin": return <Admin />;
      default: return <Overview goTo={setTab} />;
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="side-brand"><span className="dot" /><b>NEXUS</b></div>
        <nav className="nav">
          {nav.map((n) => {
            const Ico = n.icon;
            return (
              <button key={n.id} className={`nav-item ${tab === n.id ? "active" : ""}`}
                onClick={() => setTab(n.id)} data-testid={`nav-${n.id}`}>
                <Ico /> {n.label}
                {n.tag && <span className="nav-tag">{n.tag}</span>}
              </button>
            );
          })}
        </nav>
        <div className="side-foot">
          <div className="user-chip">
            <div className="avatar">{(user.name || user.email)[0].toUpperCase()}</div>
            <div className="meta">
              <b>{user.name || "Operator"}</b>
              <span>{user.role.toUpperCase()}</span>
            </div>
          </div>
          <button className="nav-item" onClick={logout} data-testid="logout-btn"><LogOut /> Sign out</button>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div>
            <h1>{current.label}</h1>
            <div className="crumb">nexus / {current.id}</div>
          </div>
          <div className="status-pill"><span className="live" /> SYSTEM ONLINE</div>
        </div>
        <div className="content">{render()}</div>
      </main>
    </div>
  );
}
