import { useEffect, useState } from "react";

import { desktopApi, type AssistantMessage } from "../lib/desktop-api";

export function AssistantView() {
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    desktopApi.getAssistantHistory().then(setMessages).catch(() => undefined);
  }, []);

  async function ask() {
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    const userMsg: AssistantMessage = {
      role: "user",
      content: q,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    try {
      const assistant = await desktopApi.askAssistant(q);
      setMessages((prev) => [...prev, assistant]);
      await desktopApi.appendAssistantHistory(userMsg, assistant);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg.includes("conectar") ? "No se pudo conectar al servidor JAIOS." : msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="assistant-panel">
      <div className="assistant-header">
        <strong>JAIOS Assistant</strong>
        <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
          Cmd/Ctrl + Shift + J para abrir/cerrar
        </div>
      </div>
      <div className="messages">
        {messages.length === 0 && (
          <div className="msg assistant">
            Pregunta sobre ventas, documentos, licitaciones o precios. Conectado al servidor central.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={`${m.timestamp}-${i}`} className={`msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {error && <div className="status error">{error}</div>}
      </div>
      <div className="composer">
        <input
          placeholder="Pregunta a JAIOS…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
        <button className="primary" disabled={loading} onClick={ask}>
          Enviar
        </button>
      </div>
    </div>
  );
}
