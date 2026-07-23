"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  latency_ms?: number;
  fallback?: boolean;
}

export default function LotteryAIPlaygroundPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setError(null);
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);
    try {
      const res = await apiClient.postLotteryAIPlayground({
        message: text,
        session_id: sessionId || undefined,
      });
      const content = String(
        (res as Record<string, unknown>).response ??
          (res as Record<string, unknown>).content ??
          (res as Record<string, unknown>).message ??
          JSON.stringify(res),
      );
      const sid = String((res as Record<string, unknown>).session_id ?? "");
      if (sid) setSessionId(sid);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content,
        latency_ms: (res as Record<string, unknown>).latency_ms as number | undefined,
        fallback: Boolean((res as Record<string, unknown>).fallback),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al enviar mensaje");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  const clear = () => {
    setMessages([]);
    setSessionId("");
    setError(null);
  };

  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Playground</h2>
        <div className="flex items-center gap-2">
          {sessionId && (
            <span className="font-mono text-xs text-muted-foreground">
              Sesión: {sessionId.slice(0, 8)}…
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={clear} disabled={sending}>
            Limpiar
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        Sandbox multi-turno del agente IA. Los mensajes no afectan datos productivos.
      </p>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card className="flex flex-1 flex-col">
        <CardHeader>
          <CardTitle className="text-sm">Conversación</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-3">
          <div className="min-h-64 flex-1 space-y-3 overflow-y-auto rounded-lg border border-border/40 bg-muted/10 p-3">
            {messages.length === 0 && (
              <p className="text-center text-xs text-muted-foreground">
                Escribe un mensaje para comenzar.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.role === "assistant" && (
                    <p className="mt-1 text-xs opacity-60">
                      {m.latency_ms !== undefined && `${m.latency_ms} ms`}
                      {m.fallback && " · fallback"}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
                  Pensando…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <Input
              placeholder="Escribe tu consulta…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={sending}
              autoFocus
            />
            <Button type="submit" disabled={sending || !input.trim()}>
              Enviar
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
