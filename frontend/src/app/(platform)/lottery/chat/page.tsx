"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
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
  analysis_params?: Record<string, unknown> | null;
};

const STARTERS = [
  "¿Cuándo fue la última vez que salió el 57?",
  "Dame los números más frecuentes.",
  "¿Qué salió en Real el 15 de marzo de 2022?",
  "¿Hay resultados pendientes hoy?",
];

const isAdminRole = (role: string | null | undefined) =>
  Boolean(role && ["superadmin", "admin", "tenant_admin"].includes(role));

/** Lightweight markdown: bold, italics, lists, line breaks — no raw HTML. */
function SimpleMarkdown({ text }: { text: string }) {
  const blocks = useMemo(() => text.split(/\n{2,}/), [text]);
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        const isList = lines.every((l) => /^\s*([-*•]|\d+\.)\s+/.test(l) || !l.trim());
        if (isList && lines.some((l) => l.trim())) {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5">
              {lines
                .filter((l) => l.trim())
                .map((l, j) => (
                  <li key={j}>{renderInline(l.replace(/^\s*([-*•]|\d+\.)\s+/, ""))}</li>
                ))}
            </ul>
          );
        }
        return (
          <p key={i} className="whitespace-pre-wrap">
            {lines.map((line, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {renderInline(line)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(line: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(line)) !== null) {
    if (m.index > last) parts.push(line.slice(last, m.index));
    const token = m[0];
    if (token.startsWith("**")) {
      parts.push(
        <strong key={key++} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith("*")) {
      parts.push(
        <em key={key++} className="italic">
          {token.slice(1, -1)}
        </em>,
      );
    } else {
      parts.push(
        <code key={key++} className="rounded bg-muted px-1 text-[0.85em]">
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = m.index + token.length;
  }
  if (last < line.length) parts.push(line.slice(last));
  return parts;
}

export default function LotteryChatPage() {
  const router = useRouter();
  const role = getUserRole();
  const showTools = isAdminRole(role);
  const [sessions, setSessions] = useState<LotteryChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paramsOpen, setParamsOpen] = useState<Record<string, boolean>>({});

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
        analysis_params: (m.tool_payload?.analysis_params as UiMessage["analysis_params"]) || null,
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

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  };

  const send = async (text: string) => {
    if (!text.trim()) return;
    if (!ensureAuth()) return;
    setLoading(true);
    setError(null);
    try {
      let sid = sessionId;
      if (!sid) {
        const s = await apiClient.createLotteryChatSession(text.slice(0, 60));
        sid = s.id;
        setSessionId(sid);
        await refreshSessions();
      }
      setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", content: text }]);
      setInput("");
      const res = await apiClient.sendLotteryChatMessage(sid, text);
      setSuggestions(res.suggestions?.length ? res.suggestions : STARTERS);
      setMessages((prev) => [
        ...prev,
        {
          id: res.message.id,
          role: "assistant",
          content: res.message.content,
          structured: res.message.structured_content,
          tool_trace: res.message.tool_trace,
          analysis_params:
            (res.message as { analysis_params?: Record<string, unknown> }).analysis_params ||
            (res.message.structured_content as { query?: Record<string, unknown> } | null)?.query ||
            null,
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
    <AppShell title="Lottery IA" description="Analista conversacional de resultados históricos">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="flex flex-wrap gap-2">
          <Link className="text-primary underline-offset-2 hover:underline" href="/lottery">
            Inicio
          </Link>
          <Link className="text-primary underline-offset-2 hover:underline" href="/lottery/search">
            Consulta
          </Link>
        </div>
        <p className="max-w-xl text-[11px] text-muted-foreground">{DISCLAIMER}</p>
      </div>

      {/* pb keeps floating JAIOS Assistant from covering the composer */}
      <div className="grid gap-4 pb-24 lg:grid-cols-[240px_1fr]">
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

          <div className="flex-1 space-y-3 overflow-auto rounded-md border p-3">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Pregunta en lenguaje natural. Lottery IA conserva el contexto y solo pide lo que falta.
              </p>
            )}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-md p-3 text-sm ${
                  m.role === "user" ? "ml-8 bg-primary/10" : "mr-4 bg-muted/40"
                }`}
              >
                <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                  {m.role === "user" ? "Tú" : "Lottery IA"}
                </p>
                {m.role === "assistant" ? (
                  <SimpleMarkdown text={m.content} />
                ) : (
                  <p className="whitespace-pre-wrap">{m.content}</p>
                )}
                {m.role === "assistant" && (
                  <div className="mt-3 space-y-2">
                    <LotteryStructuredRenderer structured={m.structured} />
                    {m.analysis_params && (
                      <div className="rounded border bg-background/60 text-xs">
                        <button
                          type="button"
                          className="w-full px-2 py-1 text-left text-muted-foreground hover:bg-muted/50"
                          onClick={() =>
                            setParamsOpen((prev) => ({ ...prev, [m.id]: !prev[m.id] }))
                          }
                        >
                          Parámetros del análisis {paramsOpen[m.id] ? "▾" : "▸"}
                        </button>
                        {paramsOpen[m.id] && (
                          <ul className="space-y-1 px-3 pb-2 text-[11px] text-muted-foreground">
                            {Object.entries(m.analysis_params)
                              .filter(([k]) => !/uuid|source_id|sql|token|password|host|slug/i.test(k))
                              .slice(0, 12)
                              .map(([k, v]) => (
                                <li key={k}>
                                  <span className="font-medium text-foreground">{k}</span>:{" "}
                                  {typeof v === "string" || typeof v === "number" || typeof v === "boolean"
                                    ? String(v)
                                    : Array.isArray(v)
                                      ? v.slice(0, 8).map(String).join(", ")
                                      : "—"}
                                </li>
                              ))}
                          </ul>
                        )}
                      </div>
                    )}
                    {showTools && m.tool_trace && m.tool_trace.length > 0 && (
                      <p className="text-[10px] text-muted-foreground">
                        Tools:{" "}
                        {m.tool_trace
                          .map((t) => `${t.tool} (${t.status}, ${t.duration_ms}ms)`)
                          .join(" · ")}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="ghost" onClick={() => void copyText(m.content)}>
                        Copiar
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <p className="animate-pulse text-xs text-muted-foreground">Analizando datos…</p>
            )}
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
        </div>
      </div>
    </AppShell>
  );
}
