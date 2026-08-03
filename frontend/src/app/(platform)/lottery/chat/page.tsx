"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import {
  AnalysisResponse,
  type WorkspaceUiAction,
} from "@/components/lottery/ux/analysis-response";
import { EmptyState } from "@/components/lottery/ux/empty-state";
import { LoadingAnalysis } from "@/components/lottery/ux/loading-analysis";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import {
  listUxFavorites,
  listUxHistory,
  listUxShared,
  rememberUxQuery,
  type SavedUxQuery,
} from "@/lib/lottery-ux-history";
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
  query?: string;
  structured?: LotteryChatSendResponse["message"]["structured_content"];
  tool_trace?: LotteryChatSendResponse["message"]["tool_trace"];
  latency_ms?: number | null;
  rawResponse?: LotteryChatSendResponse | null;
};

type ActiveContext = NonNullable<LotteryChatSendResponse["active_context"]>;

const STARTERS = [
  "Analiza el 35.",
  "¿Cuáles son los resultados de hoy?",
  "Ver loterías activas",
];

const NEAR_BOTTOM_PX = 80;

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

export default function LotteryChatPage() {
  const router = useRouter();
  const search = useSearchParams();
  const [sessions, setSessions] = useState<LotteryChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS);
  const [activeContext, setActiveContext] = useState<ActiveContext | null>(null);
  const [sessionContext, setSessionContext] = useState<Record<string, unknown> | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showJump, setShowJump] = useState(false);
  const [stickToBottom, setStickToBottom] = useState(true);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [historyTab, setHistoryTab] = useState<"sesiones" | "recientes" | "favoritas" | "compartidas">(
    "sesiones",
  );
  const [uxHistory, setUxHistory] = useState<SavedUxQuery[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingScrollRef = useRef(false);
  const lastUserQueryRef = useRef("");

  const refreshUxHistory = useCallback(() => {
    setUxHistory(listUxHistory());
  }, []);

  useEffect(() => {
    refreshUxHistory();
  }, [refreshUxHistory]);

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
      setSessionContext(null);
      return;
    }
    const ctx = s.context || {};
    setSessionContext(ctx);
    const v4 = (ctx.conversation_v4 as Record<string, unknown>) || {};
    const la = (v4.last_analysis as Record<string, unknown>) || {};
    const inv = (v4.active_investigation as Record<string, unknown>) || {};
    const invStatus = String(inv.status || "");
    const invActive = invStatus === "active";
    const nums =
      (invActive ? (inv.subjects as string[]) : null) ||
      (v4.active_numbers as string[]) ||
      (ctx.last_numbers as string[]) ||
      [];
    const tables = invActive
      ? (((inv.time_window as Record<string, unknown>) || {}).tables as string[]) || []
      : [];
    setActiveContext({
      number: (nums[0] as string | number) ?? (la.observed as string | number) ?? null,
      numbers: nums,
      analyzing: invActive
        ? String(inv.topic || (nums.length ? `número ${nums[0]}` : ""))
        : undefined,
      relation: invActive ? (inv.relation as string) || (v4.active_relation as string) : undefined,
      investigation_id: invActive ? (inv.investigation_id as string) : undefined,
      investigation_status: invStatus || undefined,
      investigation_topic: invActive ? (inv.topic as string) : undefined,
      tables,
      tables_label: tables.length ? tables.join(" y ") : undefined,
      expires_at: invActive ? (inv.expires_at as string) : undefined,
      date: (la.date as string) || (v4.active_date as string) || null,
      lottery: (la.lottery as string) || (ctx.last_lottery as string) || null,
      primary_candidate:
        (la.primary as number) ?? (v4.current_primary_candidate as number) ?? null,
      alternatives: (v4.current_alternatives as number[]) || [],
      summary: (v4.conversation_summary as string) || null,
    } as ActiveContext);
  };

  const loadMessages = useCallback(async (id: string) => {
    const res = await apiClient.listLotteryChatMessages(id);
    const items = res.items.map((m: LotteryChatMessage) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      structured: (m.tool_payload?.structured_content as UiMessage["structured"]) || null,
      tool_trace: (m.tool_payload?.tool_trace as UiMessage["tool_trace"]) || [],
      latency_ms: (m.tool_payload?.latency_ms as number | undefined) ?? null,
    }));
    // attach preceding user query to assistant messages for meta panel
    let lastQ = "";
    setMessages(
      items.map((m) => {
        if (m.role === "user") {
          lastQ = m.content;
          return m;
        }
        return { ...m, query: lastQ };
      }),
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
      setSessionContext(null);
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
    lastUserQueryRef.current = draft;
    rememberUxQuery(draft);
    refreshUxHistory();
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
      if (res.context) setSessionContext(res.context);
      setMessages((prev) => [
        ...prev,
        {
          id: res.message.id,
          role: "assistant",
          content: res.message.content,
          query: draft,
          structured: res.message.structured_content,
          tool_trace: res.message.tool_trace,
          latency_ms: res.latency_ms,
          rawResponse: res,
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

  const workspaceActionText = (action: WorkspaceUiAction): string => {
    switch (action.type) {
      case "filter_lottery":
        return `Filtrar solo ${action.lottery}.`;
      case "sort_recent":
        return "Ordenar por fecha más reciente.";
      case "breakdown_positions":
        return "Ordenar y visualizar por posición.";
      case "export_excel":
        return "Exportar Excel.";
      case "next_page":
        return "Ver más.";
      case "custom":
        return action.text;
      default:
        return "";
    }
  };

  const onWorkspaceAction = async (action: WorkspaceUiAction) => {
    const text = workspaceActionText(action);
    if (!text) return;
    await send(text);
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

  const closeInvestigation = async () => {
    if (!sessionId) return;
    try {
      const res = await apiClient.closeLotteryChatInvestigation(sessionId);
      if (res.active_context) setActiveContext(res.active_context as ActiveContext);
      else setActiveContext(null);
      if (res.context) setSessionContext(res.context);
      await refreshSessions();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar la investigación");
    }
  };

  const changeInvestigation = () => {
    setInput("Ahora analiza el ");
    textareaRef.current?.focus();
  };

  const deleteSession = async (id: string) => {
    if (!window.confirm("¿Eliminar esta conversación?")) return;
    await apiClient.deleteLotteryChatSession(id);
    if (sessionId === id) {
      setSessionId(null);
      setMessages([]);
      setActiveContext(null);
      setSessionContext(null);
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
    if (
      !activeContext?.number &&
      !activeContext?.numbers?.length &&
      !activeContext?.primary_candidate &&
      !activeContext?.analyzing &&
      !activeContext?.investigation_id
    ) {
      return null;
    }
    const nums = (activeContext.numbers as string[] | undefined) || [];
    const numberLabel =
      nums.length >= 2
        ? nums.slice(0, 4).join(" · ")
        : String(activeContext.number ?? nums[0] ?? "—");
    const status = String(activeContext.investigation_status || "active");
    const statusLabel =
      status === "closed" ? "Cerrada" : status === "expired" ? "Expirada" : "Activa";
    const tables =
      activeContext.tables_label ||
      ((activeContext.tables as string[] | undefined) || []).join(" y ") ||
      "1 y 2";
    return {
      numberLabel,
      tables,
      statusLabel,
      topic: activeContext.investigation_topic || activeContext.analyzing || null,
      filters: activeContext.filters_label || null,
      active: status === "active" || (!activeContext.investigation_status && Boolean(numberLabel)),
    };
  }, [activeContext]);

  const historyItems =
    historyTab === "favoritas"
      ? listUxFavorites()
      : historyTab === "compartidas"
        ? listUxShared()
        : historyTab === "recientes"
          ? uxHistory
          : null;

  return (
    <AppShell title="Lottery IA" description="Plataforma de análisis inteligente">
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

      <div className="grid gap-4 pb-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="h-[min(78vh,820px)] overflow-hidden">
          <CardContent className="flex h-full flex-col gap-2 py-4">
            <Button className="w-full" onClick={() => void startSession()} disabled={loading}>
              Nueva conversación
            </Button>

            <div className="flex flex-wrap gap-1">
              {(
                [
                  ["sesiones", "Sesiones"],
                  ["recientes", "Recientes"],
                  ["favoritas", "Favoritas"],
                  ["compartidas", "Compartidas"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className={`rounded-full px-2.5 py-1 text-[11px] ${
                    historyTab === id
                      ? "bg-primary/15 font-medium text-primary"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                  onClick={() => {
                    setHistoryTab(id);
                    refreshUxHistory();
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pt-1">
              {historyTab === "sesiones" &&
                sessions.map((s) => (
                  <div
                    key={s.id}
                    className={`rounded-xl px-2 py-1.5 text-left text-xs hover:bg-muted ${
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

              {historyItems &&
                (historyItems.length === 0 ? (
                  <p className="px-1 py-4 text-xs text-muted-foreground">Sin consultas aún.</p>
                ) : (
                  historyItems.map((h) => (
                    <div key={h.id} className="rounded-xl px-2 py-1.5 text-xs hover:bg-muted">
                      <button
                        type="button"
                        className="block w-full truncate text-left font-medium"
                        onClick={() => void send(h.text)}
                        title="Repetir consulta"
                      >
                        {h.text}
                      </button>
                      <p className="text-[10px] text-muted-foreground">
                        {new Date(h.lastRunAt).toLocaleString("es-DO", {
                          day: "2-digit",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                        {h.favorite ? " · ★" : ""}
                        {h.shared ? " · compartida" : ""}
                      </p>
                      <button
                        type="button"
                        className="mt-0.5 text-[10px] text-primary"
                        onClick={() => void send(h.text)}
                      >
                        Repetir consulta
                      </button>
                    </div>
                  ))
                ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex h-[min(78vh,820px)] flex-col overflow-hidden rounded-2xl border border-border/60 bg-background shadow-sm">
          {contextLabel && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-muted/15 px-3 py-2 text-[11px]">
              <div className="space-y-0.5 text-muted-foreground">
                <p className="font-medium text-foreground/90">Investigación activa</p>
                <p>
                  <span className="font-medium text-foreground/80">Número:</span>{" "}
                  {contextLabel.numberLabel}
                </p>
                <p>
                  <span className="font-medium text-foreground/80">Tabla:</span>{" "}
                  {contextLabel.tables}
                </p>
                <p>
                  <span className="font-medium text-foreground/80">Estado:</span>{" "}
                  {contextLabel.statusLabel}
                </p>
                {contextLabel.topic && (
                  <p className="text-[10px] text-muted-foreground/80">{contextLabel.topic}</p>
                )}
                {contextLabel.filters && (
                  <p className="text-[10px] text-muted-foreground/80">{contextLabel.filters}</p>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                {contextLabel.active && (
                  <>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={!sessionId || loading}
                      onClick={changeInvestigation}
                    >
                      Cambiar investigación
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={!sessionId || loading}
                      onClick={() => void closeInvestigation()}
                    >
                      Cerrar investigación
                    </Button>
                  </>
                )}
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!sessionId || loading}
                  onClick={() => void clearContext()}
                >
                  Limpiar contexto
                </Button>
              </div>
            </div>
          )}

          {error && (
            <div className="mx-3 mt-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          )}

          <div className="relative min-h-0 flex-1">
            <div
              ref={scrollRef}
              onScroll={onScrollPane}
              className="absolute inset-0 overflow-y-auto px-3 py-3 sm:px-4"
            >
              {messages.length === 0 && !loading && (
                <EmptyState
                  title="Conversando con un analista de datos"
                  body="Haz una pregunta en lenguaje natural. Lottery IA interpreta, resume, visualiza y luego te deja explorar."
                  action={
                    <div className="flex flex-wrap justify-center gap-2">
                      {STARTERS.map((s) => (
                        <Button key={s} size="sm" variant="outline" onClick={() => void send(s)}>
                          {s}
                        </Button>
                      ))}
                    </div>
                  }
                />
              )}

              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`mb-4 flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "user" ? (
                    <div className="max-w-[min(100%,420px)] rounded-2xl bg-primary px-3.5 py-2.5 text-sm text-primary-foreground shadow-sm">
                      <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    </div>
                  ) : (
                    <div className="w-full min-w-0 max-w-full">
                      <AnalysisResponse
                        content={m.content}
                        structured={m.structured}
                        query={m.query || lastUserQueryRef.current}
                        activeContext={activeContext}
                        toolTrace={m.tool_trace}
                        latencyMs={m.latency_ms}
                        sessionContext={sessionContext}
                        response={m.rawResponse}
                        showSidePanel
                        onWorkspaceAction={onWorkspaceAction}
                      />
                    </div>
                  )}
                </div>
              ))}

              {loading && <LoadingAnalysis label="Interpretando el histórico…" />}
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

          <div className="shrink-0 space-y-2 border-t bg-background/95 px-3 py-2 backdrop-blur">
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
                placeholder="Pregunta a Lottery IA…"
                className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
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
                Analizar
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
                            query: lastUserQueryRef.current,
                            structured: res.message.structured_content,
                            tool_trace: res.message.tool_trace,
                            latency_ms: res.latency_ms,
                            rawResponse: res,
                          },
                        ];
                      });
                      if (res.active_context) setActiveContext(res.active_context);
                      if (res.context) setSessionContext(res.context);
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
