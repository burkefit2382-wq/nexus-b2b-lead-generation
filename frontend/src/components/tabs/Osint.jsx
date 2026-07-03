import React, { useState } from "react";
import api from "../../lib/api";
import {
  Server, FileSearch, Globe, MapPin, Smartphone, AtSign,
  ShieldAlert, Network, ScanLine, Search, Crosshair,
} from "lucide-react";

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
