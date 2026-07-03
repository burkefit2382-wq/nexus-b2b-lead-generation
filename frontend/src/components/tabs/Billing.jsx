import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { CreditCard } from "lucide-react";

export function Billing() {
  const { user, refreshUser } = useAuth();
  const [pkgs, setPkgs] = useState([]);
  const [busy, setBusy] = useState("");
  const [poll, setPoll] = useState(null);

  useEffect(() => {
    api.get("/payments/packages").then((r) => setPkgs(r.data)).catch(() => {});
    const sid = new URLSearchParams(window.location.search).get("session_id");
    if (sid) startPolling(sid);
    // eslint-disable-next-line
  }, []);

  const startPolling = async (sid, attempt = 0) => {
    setPoll("Verifying payment…");
    if (attempt > 6) { setPoll("Still processing — check back shortly."); return; }
    try {
      const r = await api.get(`/payments/status/${sid}`);
      if (r.data.payment_status === "paid") {
        setPoll(r.data.kind === "lead" ? "✅ Payment complete — lead unlocked! Open the Lead Engine to view full contact." : "✅ Payment complete — credits added!");
        await refreshUser();
        window.history.replaceState({}, "", window.location.pathname);
        return;
      }
      if (r.data.status === "expired") { setPoll("Session expired."); return; }
      setTimeout(() => startPolling(sid, attempt + 1), 2000);
    } catch (e) { setPoll("Could not verify payment."); }
  };

  const buy = async (id) => {
    setBusy(id);
    try {
      const r = await api.post("/payments/checkout", { package_id: id, origin_url: window.location.origin });
      window.location.href = r.data.url;
    } catch (e) { alert(e.response?.data?.detail || e.message); setBusy(""); }
  };

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span>Billing · Lead Credits</span>
        <span className="mono" style={{ fontSize: 13, color: "var(--accent)" }}>
          <CreditCard size={14} style={{ verticalAlign: -2, marginRight: 6 }} />{user?.credits ?? 0} credits available
        </span>
      </div>
      {poll && <div className="key-reveal" data-testid="billing-poll"><span className="mono" style={{ color: "var(--accent)" }}>{poll}</span></div>}
      <div className="osint-grid">
        {pkgs.map((p) => (
          <div className="tool-card" key={p.id} style={{ cursor: "default" }} data-testid={`pkg-${p.id}`}>
            <div className="ico"><CreditCard size={18} /></div>
            <h4>{p.name}</h4>
            <div style={{ fontFamily: "var(--head)", fontSize: 34, fontWeight: 700, margin: "8px 0" }}>${p.amount}</div>
            <p style={{ marginBottom: 14 }}><b style={{ color: "var(--accent)" }}>{p.credits} credits</b> · unlock {p.credits} premium leads</p>
            <button className="btn btn-sm" onClick={() => buy(p.id)} disabled={busy === p.id} data-testid={`buy-${p.id}`}>
              {busy === p.id ? <span className="spinner" /> : "Buy Now"}
            </button>
          </div>
        ))}
      </div>
      <p className="mono" style={{ fontSize: 11, color: "var(--muted)", marginTop: 18 }}>
        1 credit unlocks 1 scraped lead's full contact. Secure checkout via Stripe (test mode). Card: 4242 4242 4242 4242.
      </p>
    </div>
  );
}
