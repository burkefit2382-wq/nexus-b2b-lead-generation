import React, { useEffect, useRef, useState } from "react";
import api from "../../lib/api";
import { Bot, Send } from "lucide-react";

export function AIChat() {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("deepseek");
  const [busy, setBusy] = useState(false);
  const streamRef = useRef(null);
  useEffect(() => { streamRef.current?.scrollTo(0, streamRef.current.scrollHeight); }, [msgs, busy]);

  const send = async () => {
    const m = input.trim();
    if (!m || busy) return;
    setMsgs((x) => [...x, { id: crypto.randomUUID(), role: "user", text: m }]); setInput(""); setBusy(true);
    try {
      const r = await api.post("/enrichment/chat", { message: m, model });
      setMsgs((x) => [...x, { id: crypto.randomUUID(), role: "ai", text: r.data.response || ("⚠ " + (r.data.error || "no response")) }]);
    } catch (e) {
      setMsgs((x) => [...x, { id: crypto.randomUUID(), role: "ai", text: "⚠ " + (e.response?.data?.detail || e.message) }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="fade-in">
      <div className="section-title" style={{ justifyContent: "space-between" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 10 }}>NEXUS AI · Analyst</span>
      </div>
      <div className="panel">
        <div className="panel-head">
          <h3>Conversation</h3>
          <select className="select" value={model} onChange={(e) => setModel(e.target.value)} data-testid="chat-model">
            <option value="deepseek">DeepSeek V3.1</option>
            <option value="qwen">Qwen 2.5 32B</option>
          </select>
        </div>
        <div className="chat-wrap">
          <div className="chat-stream" ref={streamRef}>
            {!msgs.length && (
              <div className="chat-empty">
                <Bot size={42} />
                <div className="mono" style={{ fontSize: 13 }}>Ask about leads, OSINT strategy or digital footprints.</div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={m.id} className={`msg ${m.role}`} data-testid={`chat-msg-${i}`}>
                {m.role === "ai" && <span className="who">NEXUS</span>}{m.text}
              </div>
            ))}
            {busy && <div className="msg ai"><span className="who">NEXUS</span><span className="spinner lime" /></div>}
          </div>
          <div className="chat-input-row">
            <input className="search-input" style={{ flex: 1 }} placeholder="Message NEXUS…"
              value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
              data-testid="chat-input" />
            <button className="btn btn-sm" onClick={send} disabled={busy} data-testid="chat-send"><Send size={14} /></button>
          </div>
        </div>
      </div>
    </div>
  );
}
