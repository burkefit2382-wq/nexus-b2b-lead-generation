import "@/index.css";
import { useEffect, useState } from "react";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/components/Login";
import Dashboard from "@/components/Dashboard";
import Landing from "@/components/Landing";

const APP_HASHES = ["app", "dashboard", "login", "console"];

// `/` serves the public launch site; the functional NEXUS console lives at /dashboard
// (also reachable via #app/#dashboard/#login/#console).
function isAppRoute() {
  const path = window.location.pathname.toLowerCase();
  const hash = window.location.hash.replace("#", "").toLowerCase();
  return (
    path.startsWith("/dashboard") ||
    path.startsWith("/app") ||
    path.startsWith("/console") ||
    APP_HASHES.includes(hash)
  );
}

function Gate() {
  const { user, loading } = useAuth();
  if (loading || user === null) {
    return (
      <div className="loader-screen">
        <div className="brand-badge"><span className="dot" /><span className="brand-title">NEXUS</span></div>
        <div className="mono">INITIALIZING TERMINAL…</div>
      </div>
    );
  }
  return user ? <Dashboard /> : <Login />;
}

export default function App() {
  const [app, setApp] = useState(isAppRoute());

  useEffect(() => {
    const sync = () => setApp(isAppRoute());
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  if (!app) return <Landing />;

  return (
    <AuthProvider>
      <Gate />
      <Toaster position="bottom-right" theme="dark" richColors closeButton />
    </AuthProvider>
  );
}
