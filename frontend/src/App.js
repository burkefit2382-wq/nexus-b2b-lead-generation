import "@/index.css";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/components/Login";
import Dashboard from "@/components/Dashboard";

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
  return (
    <AuthProvider>
      <Gate />
      <Toaster position="bottom-right" theme="dark" richColors closeButton />
    </AuthProvider>
  );
}
