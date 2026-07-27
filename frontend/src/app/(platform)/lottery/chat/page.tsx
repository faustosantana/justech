"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { LotteryStructuredRenderer } from "@/components/lottery/lottery-structured-renderer";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

type ActiveContext = NonNullable<LotteryChatSendResponse["active_context"]>;

const STARTERS = [
  "Analiza el 35.",
  "¿Cuáles son los resultados de hoy?",
  "Ver loterías activas",
];

const NEAR_BOTTOM_PX = 80;

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

function formatSessionMeta(s: LotteryChatSession): string {
  const ctx = s.context || {};
  const v4 = (ctx.conversation_v4 as Record<string, unknown>) || {};
  const la = (v4.last_analysis as Record<string, unknown>) || {};
  const num = la.observed ?? (Array.isArray(ctx.last_numbers) ? ctx.last_numbers[0] : null);
  const when = s.last_message_at || s.updated_at || s.created_at;
  const dateBit = when
    ? new Date(when).toLocaleDateString("es-DO", { day: "2-digit", month: "short" })
    : "";
  return [num != null ? `Nº ${num}` : null, dateBit].filter(Boolean).join(" · ");
}

function AnalysisCard({ structured }: { structured: UiMessage["structured"] }) {
  if (!structured || structured.type !== "lottery_complete_analysis") return null;
  const raw = structured.data;
  const data = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const primary = (data.primary as { number?: number; reason?: string } | undefined) || {};
  const hist = (data.historical as Record<string, unknown> | undefined) || {};
  const why: string[] = [];
  const t1 = (data.table1_sources as unknown[]) || [];
  const t2 = (data.table2_confirmers as unknown[]) || [];
  const same = (data.same_day_cross as Record<string, unknown>[]) || [];
  if (t1.length) why.push(`Tabla 1 relaciona ${data.observed_number} con ${primary.number}.`);
  if (t2.length) why.push(`Tabla 2 confirma ${primary.number} mediante ${t2.join(", ")}.`);
  if (same[0]) {
    why.push(
      `Cruce del mismo día: ${same[0].origen} → ${same[0].companero} (confirmador ${same[0].confirmador}).`,
    );
  }
  if (hist.casos_equivalentes != null) {
    why.push(
      `Histórico: ${hist.casos_equivalentes} casos equivalentes, ${hist.aciertos_exactos ?? "—"} aciertos exactos.`,
    );
  }
  const rival = data.rival_comparison as { texto?: string } | undefined;
  return (
    <div className="mt-2 rounded-md border bg-background/70 p-3 text-xs text-muted-foreground">
      <p>
        <span className="font-medium text-foreground">Número analizado:</span>{" "}
        {String(data.observed_number ?? "—")}
      </p>
      <p className="mt-1">
        <span className="font-medium text-foreground">Resultado principal:</span>{" "}
        {primary.number != null ? String(primary.number) : "—"}
      </p>
      {why.length > 0 && (
        <div className="mt-2">
          <p className="font-medium text-foreground">Por qué:</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {why.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {rival?.texto && (
        <p className="mt-2">
          <span className="font-medium text-foreground">Comparación:</span> {rival.texto}
        </p>
      )}
    </div>
  );
}

export default function LotteryChatPage() {
  const router = useRouter();
  const search = useSearchParams();
  const [sessions, setSessions] = useState<LotteryChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS);
  const [activeContext, setActiveContext] = useState<ActiveContext | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showJump, setShowJump] = useState(false);
  const [stickToBottom, setStickToBottom] = useState(true);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingScrollRef = useRef(false);

  useEffect(() => {
    const q = search.get("q") || "";
    const n = search.get("number") || "";
    const lottery = search.get("lottery") || "";
    const date = search.get("date") || "";
    const highlight = search.get("highlight") || "";
    const withN = search.get("with") || "";
    if (q) setInput(q);
    const contextual = [
      n ? `Analiza el ${n}.` : null,
      n && highlight ? `¿Por qué el ${highlight}?` : null,
      n && withN ? `Analiza el ${n} con el ${withN}.` : null,
      n ? `Muéstrame el comportamiento histórico del ${n}.` : null,
      highlight ? `¿Por qué no el 07?` : null,
      lottery && date && n
        ? `Usa el contexto del ${n} en ${lottery} (${date}); no inventes relaciones.`
        : null,
    ].filter(Boolean) as string[];
    if (contextual.length) setSuggestions(contextual);
  }, [search]);

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
    return res.items;
  }, []);

  const applyContextFromSession = (s: LotteryChatSession | undefined) => {
    if (!s) {
      setActiveContext(null);
      return;
    }
    const ctx = s.context || {};
    const v4 = (ctx.conversation_v4 as Record<string, unknown>) || {};
    const la = (v4.last_analysis as Record<string, unknown>) || {};
    const nums = (v4.active_numbers as string[]) || (ctx.last_numbers as string[]) || [];
    setActiveContext({
      number: (la.observed as string | number) ?? nums[0] ?? null,
      date: (la.date as string) || (v4.active_date as string) || null,
      lottery: (la.lottery as string) || (ctx.last_lottery as string) || null,
      primary_candidate:
        (la.primary as number) ?? (v4.current_primary_candidate as number) ?? null,
      alternatives: (v4.current_alternatives as number[]) || [],
      summary: (v4.conversation_summary as string) || null,
    });
  };

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
    pendingScrollRef.current = true;
    setStickToBottom(true);
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
      setActiveContext(null);
      await refreshSessions();
      pendingScrollRef.current = true;
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
        const items = await refreshSessions();
        if (items.length && !sessionId) {
          const last = items[0];
          setSessionId(last.id);
          applyContextFromSession(last);
          await loadMessages(last.id);
        }
      } catch {
        /* ignore initial */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- restore once on mount
  }, [ensureAuth, refreshSessions, loadMessages]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    bottomRef.current?.scrollIntoView({ block: "end", behavior });
    setShowJump(false);
    setStickToBottom(true);
  }, []);

  useLayoutEffect(() => {
    if (!stickToBottom && !pendingScrollRef.current) return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    pendingScrollRef.current = false;
    setShowJump(false);
  }, [messages, loading, stickToBottom]);

  const onScrollPane = () => {
    const el = scrollRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    const near = dist <= NEAR_BOTTOM_PX;
    setStickToBottom(near);
    setShowJump(!near && messages.length > 0);
  };

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    if (!ensureAuth()) return;
    setLoading(true);
    setError(null);
    setStickToBottom(true);
    pendingScrollRef.current = true;
    const draft = trimmed;
    try {
      let sid = sessionId;
      if (!sid) {
        const s = await apiClient.createLotteryChatSession(draft.slice(0, 60));
        sid = s.id;
        setSessionId(sid);
        await refreshSessions();
      }
      setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", content: draft }]);
      setInput("");
      if (textareaRef.current) textareaRef.current.style.height = "auto";
      const res = await apiClient.sendLotteryChatMessage(sid, draft);
      setSuggestions(res.suggestions?.length ? res.suggestions : STARTERS);
      if (res.active_context) setActiveContext(res.active_context);
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
      setInput(draft);
      setError(err instanceof ApiError ? err.message : "Error al enviar mensaje");
    } finally {
      setLoading(false);
    }
  };

  const onSelectSession = async (id: string) => {
    setSessionId(id);
    setError(null);
    setStickToBottom(true);
    pendingScrollRef.current = true;
    try {
      const s = sessions.find((x) => x.id === id) || (await apiClient.getLotteryChatSession(id));
      applyContextFromSession(s);
      await loadMessages(id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el historial");
    }
  };

  const clearContext = async () => {
    if (!sessionId) return;
    await apiClient.clearLotteryChatContext(sessionId);
    setActiveContext(null);
    setSuggestions(STARTERS);
    await refreshSessions();
  };

  const deleteSession = async (id: string) => {
    if (!window.confirm("¿Eliminar esta conversación?")) return;
    await apiClient.deleteLotteryChatSession(id);
    if (sessionId === id) {
      setSessionId(null);
      setMessages([]);
      setActiveContext(null);
    }
    await refreshSessions();
  };

  const saveRename = async (id: string) => {
    const title = renameValue.trim();
    if (!title) {
      setRenamingId(null);
      return;
    }
    await apiClient.renameLotteryChatSession(id, title);
    setRenamingId(null);
    await refreshSessions();
  };

  const contextLabel = useMemo(() => {
    if (!activeContext?.number && !activeContext?.numbers?.length && !activeContext?.primary_candidate && !activeContext?.analyzing) {
      return null;
    }
    const nums = (activeContext.numbers as string[] | undefined) || [];
    const analyzing =
      (activeContext.analyzing as string | undefined) ||
      (nums.length >= 2 ? nums.slice(0, 4).join(" + ") : activeContext.number) ||
      "—";
    const dateBit = activeContext.date
      ? new Date(`${String(activeContext.date).slice(0, 10)}T12:00:00`).toLocaleDateString(
          "es-DO",
          { day: "numeric", month: "short", year: "numeric" },
        )
      : null;
    return {
      analyzing: [analyzing, dateBit].filter(Boolean).join(" · "),
      filters: (activeContext.filters_label as string | undefined) || null,
      primary: activeContext.primary_candidate,
    };
  }, [activeContext]);

  return (
    <AppShell title="Chat inteligente" description="Asistente conversacional de Lottery IA">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="flex flex-wrap gap-2">
          <Link className="text-primary underline-offset-2 hover:underline" href="/lottery">
            Inicio
          </Link>
          <Link className="text-primary underline-offset-2 hover:underline" href="/lottery/search">
            Consulta
          </Link>
          <Link className="text-primary underline-offset-2 hover:underline" href="/lottery/analyze">
            Analizar
          </Link>
        </div>
        <p className="max-w-xl text-[11px] text-muted-foreground">{DISCLAIMER}</p>
      </div>

      <div className="grid gap-4 pb-6 lg:grid-cols-[260px_1fr]">
        <Card className="h-[min(72vh,720px)] overflow-hidden">
          <CardContent className="flex h-full flex-col gap-2 py-4">
            <Button className="w-full" onClick={() => void startSession()} disabled={loading}>
              Nueva conversación
            </Button>
            <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pt-1">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className={`rounded px-2 py-1.5 text-left text-xs hover:bg-muted ${
                    sessionId === s.id ? "bg-muted font-medium" : ""
                  }`}
                >
                  {renamingId === s.id ? (
                    <form
                      className="flex gap-1"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void saveRename(s.id);
                      }}
                    >
                      <input
                        className="min-w-0 flex-1 rounded border bg-background px-1 py-0.5"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        autoFocus
                      />
                      <button type="submit" className="text-[10px] text-primary">
                        OK
                      </button>
                    </form>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="block w-full truncate text-left"
                        onClick={() => void onSelectSession(s.id)}
                      >
                        {s.title || "Sin título"}
                      </button>
                      <p className="truncate text-[10px] text-muted-foreground">
                        {formatSessionMeta(s)}
                      </p>
                      <div className="mt-0.5 flex gap-2 text-[10px]">
                        <button
                          type="button"
                          className="text-muted-foreground hover:text-foreground"
                          onClick={() => {
                            setRenamingId(s.id);
                            setRenameValue(s.title || "");
                          }}
                        >
                          Renombrar
                        </button>
                        <button
                          type="button"
                          className="text-muted-foreground hover:text-destructive"
                          onClick={() => void deleteSession(s.id)}
                        >
                          Eliminar
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex h-[min(72vh,720px)] flex-col overflow-hidden rounded-md border bg-background">
          {contextLabel && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-muted/20 px-3 py-1.5 text-[11px]">
              <div className="space-y-0.5 text-muted-foreground">
                <p>
                  <span className="font-medium text-foreground/80">
                    {String(contextLabel.analyzing || "").includes("coincid")
                      ? "Investigación:"
                      : "Analizando:"}
                  </span>{" "}
                  {contextLabel.analyzing || "—"}
                </p>
                {contextLabel.filters && (
                  <p className="text-[10px] text-muted-foreground/80">{contextLabel.filters}</p>
                )}
                {contextLabel.primary != null && (
                  <p>
                    <span className="font-medium text-foreground/80">Candidato actual:</span>{" "}
                    {contextLabel.primary}
                  </p>
                )}
              </div>
              <Button size="sm" variant="ghost" disabled={!sessionId || loading} onClick={() => void clearContext()}>
                Limpiar contexto
              </Button>
            </div>
          )}

          {error && (
            <div className="mx-3 mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          )}

          <div className="relative min-h-0 flex-1">
            <div
              ref={scrollRef}
              onScroll={onScrollPane}
              className="absolute inset-0 overflow-y-auto px-3 py-3"
            >
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Pregunta en lenguaje natural. Conservo el contexto y solo pido lo imprescindible.
                </p>
              )}
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`mb-3 flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "assistant" && (
                    <div
                      className="mr-2 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border/70 bg-muted text-[10px] font-semibold text-muted-foreground"
                      aria-hidden
                    >
                      IA
                    </div>
                  )}
                  <div
                    className={`max-w-[min(100%,520px)] rounded-2xl px-3.5 py-2.5 text-sm shadow-sm ${
                      m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "border border-border/60 bg-card text-foreground"
                    }`}
                  >
                    {m.role === "user" ? (
                      <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    ) : (
                      <div className="space-y-2">
                        <SimpleMarkdown text={m.content} />
                        <AnalysisCard structured={m.structured} />
                        {m.structured && m.structured.type !== "lottery_complete_analysis" && (
                          <div className="mt-2">
                            <LotteryStructuredRenderer structured={m.structured} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="inline-flex h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                  <span className="animate-pulse">Analizando el histórico…</span>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {showJump && (
              <button
                type="button"
                className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full border bg-background px-3 py-1.5 text-xs shadow-sm"
                onClick={() => scrollToBottom("smooth")}
              >
                Ir al mensaje más reciente
              </button>
            )}
          </div>

          <div className="shrink-0 space-y-2 border-t bg-background px-3 py-2">
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
              className="flex items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void send(input);
              }}
            >
              <textarea
                ref={textareaRef}
                value={input}
                rows={1}
                disabled={loading}
                placeholder="Escribe tu consulta…"
                className="max-h-32 min-h-[40px] flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
                onChange={(e) => {
                  setInput(e.target.value);
                  const el = e.target;
                  el.style.height = "auto";
                  el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send(input);
                  }
                }}
              />
              <Button type="submit" disabled={loading || !input.trim()}>
                Enviar
              </Button>
              {sessionId && error && (
                <Button
                  type="button"
                  variant="secondary"
                  disabled={loading}
                  onClick={async () => {
                    setLoading(true);
                    setError(null);
                    try {
                      const res = await apiClient.retryLotteryChatMessage(sessionId);
                      setStickToBottom(true);
                      pendingScrollRef.current = true;
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
                      if (res.active_context) setActiveContext(res.active_context);
                      setSuggestions(res.suggestions?.length ? res.suggestions : STARTERS);
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
      </div>
    </AppShell>
  );
}
