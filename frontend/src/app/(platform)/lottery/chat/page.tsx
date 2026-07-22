"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { LotteryStructuredRenderer } from "@/components/lottery/lottery-structured-renderer";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import {
  canAccessLotteryModule,
  DISCLAIMER,
  type LotteryChatMessage,
  type LotteryChatSendResponse,
  type LotteryChatSession,
} from "@/lib/lottery";

type UiMessage = {
  id: string;
  role: string;
  content: string;
  structured?: LotteryChatSendResponse["message"]["structured_content"];
  tool_trace?: LotteryChatSendResponse["message"]["tool_trace"];
};

const STARTERS = [
  "¿Qué salió en Real el 15 de marzo de 2022?",
  "¿Y los siete días siguientes?",
  "¿Cuáles se repitieron?",
  "¿Y cuáles también aparecieron en Nacional Noche?",
  "¿Cuándo volvió a salir el 01?",
  "Muéstrame los siguientes siete sorteos.",
];

export default function LotteryChatPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<LotteryChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNote, setFallbackNote] = useState(false);

  const ensureAuth = useCallback(() => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return false;
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError("Sin permiso lottery.chat / lottery.access");
      return false;
    }
    return true;
  }, [router]);

  const refreshSessions = useCallback(async () => {
    const res = await apiClient.listLotteryChatSessions();
    setSessions(res.items);
  }, []);

  const loadMessages = useCallback(async (id: string) => {
    const res = await apiClient.listLotteryChatMessages(id);
    setMessages(
      res.items.map((m: LotteryChatMessage) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        structured: (m.tool_payload?.structured_content as UiMessage["structured"]) || null,
        tool_trace: (m.tool_payload?.tool_trace as UiMessage["tool_trace"]) || [],
      })),
    );
  }, []);

  const startSession = useCallback(async () => {
    if (!ensureAuth()) return;
    setLoading(true);
    setError(null);
    try {
      const s = await apiClient.createLotteryChatSession("Nueva consulta");
      setSessionId(s.id);
      setMessages([]);
      setSuggestions(STARTERS);
      await refreshSessions();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la sesión");
    } finally {
      setLoading(false);
    }
  }, [ensureAuth, refreshSessions]);

  useEffect(() => {
    if (!ensureAuth()) return;
    void (async () => {
      try {
        await refreshSessions();
      } catch {
        /* ignore initial */
      }
    })();
  }, [ensureAuth, refreshSessions]);

  const send = async (text: string) => {
    if (!text.trim()) return;
    if (!ensureAuth()) return;
    setLoading(true);
    setError(null);
    setFallbackNote(false);
    try {
      let sid = sessionId;
      if (!sid) {
        const s = await apiClient.createLotteryChatSession(text.slice(0, 60));
        sid = s.id;
        setSessionId(sid);
        await refreshSessions();
      }
      setMessages((prev) => [
        ...prev,
        { id: `u-${Date.now()}`, role: "user", content: text },
      ]);
      setInput("");
      const res = await apiClient.sendLotteryChatMessage(sid, text);
      setFallbackNote(Boolean(res.synthesis_fallback));
      setSuggestions(res.suggestions?.length ? res.suggestions : STARTERS);
      setMessages((prev) => [
        ...prev,
        {
          id: res.message.id,
          role: "assistant",
          content: res.message.content,
          structured: res.message.structured_content,
          tool_trace: res.message.tool_trace,
        },
      ]);
      await refreshSessions();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al enviar mensaje");
    } finally {
      setLoading(false);
    }
  };

  const onSelectSession = async (id: string) => {
    setSessionId(id);
    setError(null);
    try {
      await loadMessages(id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el historial");
    }
  };

  return (
    <AppShell title="Lotería IA" description="Chat histórico con tools tipadas — sin predicción">
      <div className="mb-3 flex flex-wrap gap-2 text-sm">
        <Link className="text-primary underline-offset-2 hover:underline" href="/lottery">
          Inicio
        </Link>
        <Link className="text-primary underline-offset-2 hover:underline" href="/lottery/search">
          Consulta
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <Card>
          <CardContent className="space-y-2 py-4">
            <Button className="w-full" onClick={() => void startSession()} disabled={loading}>
              Nueva conversación
            </Button>
            {sessionId && (
              <Button
                className="w-full"
                variant="outline"
                onClick={async () => {
                  if (!sessionId) return;
                  await apiClient.clearLotteryChatContext(sessionId);
                  setSuggestions(STARTERS);
                }}
              >
                Limpiar contexto
              </Button>
            )}
            <div className="max-h-[50vh] space-y-1 overflow-auto pt-2">
              {sessions.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`block w-full truncate rounded px-2 py-1.5 text-left text-xs hover:bg-muted ${
                    sessionId === s.id ? "bg-muted font-medium" : ""
                  }`}
                  onClick={() => void onSelectSession(s.id)}
                >
                  {s.title || "Sin título"}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex min-h-[60vh] flex-col gap-3">
          {error && (
            <Card className="border-destructive/40">
              <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
            </Card>
          )}
          {fallbackNote && (
            <p className="text-xs text-amber-700 dark:text-amber-400">
              Redacción LLM no disponible — se muestran resultados estructurados.
            </p>
          )}

          <div className="flex-1 space-y-3 overflow-auto rounded-md border p-3">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Pregunta por resultados históricos. El asistente solo usa tools tipadas sobre
                PostgreSQL.
              </p>
            )}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-md p-3 text-sm ${
                  m.role === "user" ? "bg-primary/10 ml-8" : "bg-muted/40 mr-4"
                }`}
              >
                <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                  {m.role === "user" ? "Tú" : "Lotería IA"}
                </p>
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.role === "assistant" && (
                  <div className="mt-3 space-y-2">
                    <LotteryStructuredRenderer structured={m.structured} />
                    {m.tool_trace && m.tool_trace.length > 0 && (
                      <p className="text-[10px] text-muted-foreground">
                        Tools:{" "}
                        {m.tool_trace
                          .map((t) => `${t.tool} (${t.status}, ${t.duration_ms}ms)`)
                          .join(" · ")}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <Button
                key={s}
                size="sm"
                variant="outline"
                disabled={loading}
                onClick={() => void send(s)}
              >
                {s}
              </Button>
            ))}
          </div>

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu consulta histórica…"
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              Enviar
            </Button>
            {sessionId && (
              <Button
                type="button"
                variant="secondary"
                disabled={loading}
                onClick={async () => {
                  setLoading(true);
                  try {
                    const res = await apiClient.retryLotteryChatMessage(sessionId);
                    setMessages((prev) => {
                      const withoutLastAssistant =
                        prev.length && prev[prev.length - 1].role === "assistant"
                          ? prev.slice(0, -1)
                          : prev;
                      return [
                        ...withoutLastAssistant,
                        {
                          id: res.message.id,
                          role: "assistant",
                          content: res.message.content,
                          structured: res.message.structured_content,
                          tool_trace: res.message.tool_trace,
                        },
                      ];
                    });
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "Retry falló");
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                Reintentar
              </Button>
            )}
          </form>

          <p className="text-xs text-muted-foreground">{DISCLAIMER}</p>
        </div>
      </div>
    </AppShell>
  );
}
