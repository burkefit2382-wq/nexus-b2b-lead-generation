import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { Overview, Osint, AIChat, ApiKeys, Reports, Admin, PeopleIntel, Billing } from "./tabs";
import { Leads } from "./Leads";
import { Scrapers } from "./Scrapers";
import {
  LayoutGrid, Crosshair, Users2, Bot, KeyRound, ScrollText, ShieldCheck, LogOut, Radar,
  UserSearch, CreditCard
} from "lucide-react";

const NAV = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "scrapers", label: "Lead Scrapers", icon: Radar, tag: "24/7" },
  { id: "leads", label: "Lead Engine", icon: Users2 },
  { id: "people", label: "People Intel", icon: UserSearch },
  { id: "osint", label: "OSINT Tools", icon: Crosshair, tag: "12" },
  { id: "ai", label: "NEXUS AI", icon: Bot },
  { id: "reports", label: "Intel Reports", icon: ScrollText },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "keys", label: "API Keys", icon: KeyRound },
];

const TAB_VIEWS = {
  scrapers: () => <Scrapers />,
  leads: () => <Leads />,
  people: () => <PeopleIntel />,
  billing: () => <Billing />,
  osint: () => <Osint />,
  ai: () => <AIChat />,
  reports: () => <Reports />,
  keys: () => <ApiKeys />,
  admin: () => <Admin />,
};

/* Tab state + cross-component navigation (Stripe return + "nexus-goto" events) */
function useDashboardTab() {
  const hasSession = new URLSearchParams(window.location.search).get("session_id");
  const [tab, setTab] = useState(hasSession ? "billing" : "overview");
  useEffect(() => {
    const handler = (e) => setTab(e.detail);
    window.addEventListener("nexus-goto", handler);
    return () => window.removeEventListener("nexus-goto", handler);
  }, []);
  return [tab, setTab];
}

function Sidebar({ nav, tab, setTab, user, logout }) {
  return (
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
  );
}

function Topbar({ current, credits, onCreditsClick }) {
  return (
    <div className="topbar">
      <div>
        <h1>{current.label}</h1>
        <div className="crumb">nexus / {current.id}</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <button className="status-pill" style={{ color: "var(--accent)", cursor: "pointer" }} onClick={onCreditsClick} data-testid="topbar-credits">
          <CreditCard size={13} /> {credits ?? 0} credits
        </button>
        <div className="status-pill"><span className="live" /> SYSTEM ONLINE</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [tab, setTab] = useDashboardTab();
  const nav = [...NAV, ...(user.role === "admin" ? [{ id: "admin", label: "Admin", icon: ShieldCheck }] : [])];
  const current = nav.find((n) => n.id === tab) || nav[0];

  const renderTab = useCallback(() => {
    const view = TAB_VIEWS[tab];
    return view ? view() : <Overview goTo={setTab} />;
  }, [tab, setTab]);

  return (
    <div className="app-shell">
      <Sidebar nav={nav} tab={tab} setTab={setTab} user={user} logout={logout} />
      <main className="main">
        <Topbar current={current} credits={user.credits} onCreditsClick={() => setTab("billing")} />
        <div className="content">{renderTab()}</div>
      </main>
    </div>
  );
}
