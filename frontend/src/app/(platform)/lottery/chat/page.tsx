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
import { cn } from "@/lib/utils";

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
  const [success, setSuccess] = useState<string | null>(null);
  const [showJump, setShowJump] = useState(false);
  const [stickToBottom, setStickToBottom] = useState(true);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [historyTab, setHistoryTab] = useState<"sesiones" | "recientes" | "favoritas" | "compartidas">(
    "sesiones",
  );
  const [uxHistory, setUxHistory] = useState<SavedUxQuery[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [confirmBulk, setConfirmBulk] = useState(false);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [deleteAllPhrase, setDeleteAllPhrase] = useState("");
  const [moreOpen, setMoreOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingScrollRef = useRef(false);
  const lastUserQueryRef = useRef("");

  const flashSuccess = useCallback((msg: string) => {
    setSuccess(msg);
    window.setTimeout(() => setSuccess(null), 3200);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    setSelectionMode(false);
    setConfirmBulk(false);
  }, []);

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

  const resetOpenConversation = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setActiveContext(null);
    setSessionContext(null);
    setSuggestions(STARTERS);
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
    const items = res.items.map((m: LotteryChatMessage) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      structured: (m.tool_payload?.structured_content as UiMessage["structured"]) || null,
      tool_trace: (m.tool_payload?.tool_trace as UiMessage["tool_trace"]) || [],
      latency_ms: (m.tool_payload?.latency_ms as number | undefined) ?? null,
    }));
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
      setHistoryOpen(false);
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
    if (selectionMode) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
      return;
    }
    setSessionId(id);
    setError(null);
    setStickToBottom(true);
    pendingScrollRef.current = true;
    setHistoryOpen(false);
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
    setDeleting(true);
    setError(null);
    try {
      await apiClient.deleteLotteryChatSession(id);
      if (sessionId === id) resetOpenConversation();
      await refreshSessions();
      flashSuccess("Conversación eliminada");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    } finally {
      setDeleting(false);
    }
  };

  const toggleSelectAllVisible = () => {
    const visibleIds = sessions.map((s) => s.id);
    const allSelected =
      visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(visibleIds));
      setSelectionMode(true);
    }
  };

  const confirmBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    if (!ids.length) return;
    setDeleting(true);
    setError(null);
    try {
      const res = await apiClient.bulkDeleteLotteryChatSessions(ids);
      if (sessionId && ids.includes(sessionId)) resetOpenConversation();
      await refreshSessions();
      clearSelection();
      if (res.failed_ids.length) {
        setError(
          `Eliminadas ${res.deleted_count}. Fallaron ${res.failed_ids.length}: ${res.failed_ids.slice(0, 3).join(", ")}${res.failed_ids.length > 3 ? "…" : ""}`,
        );
      } else {
        flashSuccess(
          res.deleted_count === 1
            ? "1 conversación eliminada"
            : `${res.deleted_count} conversaciones eliminadas`,
        );
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar seleccionadas");
    } finally {
      setDeleting(false);
      setConfirmBulk(false);
    }
  };

  const confirmDeleteAllSessions = async () => {
    if (deleteAllPhrase.trim().toUpperCase() !== "ELIMINAR") return;
    setDeleting(true);
    setError(null);
    try {
      const res = await apiClient.deleteAllLotteryChatSessions();
      resetOpenConversation();
      await refreshSessions();
      clearSelection();
      setConfirmDeleteAll(false);
      setDeleteAllPhrase("");
      flashSuccess(
        res.deleted_count === 0
          ? "No había conversaciones"
          : `Se eliminaron ${res.deleted_count} conversaciones`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar todas");
    } finally {
      setDeleting(false);
    }
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
      !activeContext?.analyzing
    ) {
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

  const historyItems =
    historyTab === "favoritas"
      ? listUxFavorites()
      : historyTab === "compartidas"
        ? listUxShared()
        : historyTab === "recientes"
          ? uxHistory
          : null;

  const selectedCount = selectedIds.size;
  const allVisibleSelected =
    sessions.length > 0 && sessions.every((s) => selectedIds.has(s.id));

  const historyPanel = (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden border-border/60">
      <CardContent className="flex h-full min-h-0 flex-col gap-2 py-4">
        <div className="flex items-center gap-2">
          <Button className="min-w-0 flex-1" onClick={() => void startSession()} disabled={loading || deleting}>
            Nueva conversación
          </Button>
          <Button
            type="button"
            variant="outline"
            className="lg:hidden"
            onClick={() => setHistoryOpen(false)}
            aria-label="Cerrar conversaciones"
          >
            Cerrar
          </Button>
        </div>

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
              className={cn(
                "rounded-full px-2.5 py-1 text-[11px]",
                historyTab === id
                  ? "bg-primary/15 font-medium text-primary"
                  : "text-muted-foreground hover:bg-muted",
              )}
              onClick={() => {
                setHistoryTab(id);
                refreshUxHistory();
                if (id !== "sesiones") clearSelection();
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {historyTab === "sesiones" && (
          <div className="space-y-2 rounded-xl border border-border/50 bg-muted/20 p-2">
            {!selectionMode ? (
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-8 text-[11px]"
                  disabled={!sessions.length || deleting}
                  onClick={() => setSelectionMode(true)}
                >
                  Seleccionar
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-8 text-[11px] text-destructive"
                  disabled={!sessions.length || deleting}
                  onClick={() => {
                    setConfirmDeleteAll(true);
                    setDeleteAllPhrase("");
                  }}
                >
                  Eliminar todas
                </Button>
              </div>
            ) : (
              <div className="space-y-2" data-testid="selection-bar">
                <label className="flex items-center gap-2 text-[11px]">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-primary"
                    checked={allVisibleSelected}
                    onChange={toggleSelectAllVisible}
                    aria-label="Seleccionar todas las visibles"
                  />
                  <span>Seleccionar todas (solo visibles)</span>
                </label>
                <p className="text-[11px] text-muted-foreground">
                  {selectedCount} seleccionada{selectedCount === 1 ? "" : "s"}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-8 text-[11px]"
                    disabled={deleting}
                    onClick={clearSelection}
                  >
                    Cancelar
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    className="h-8 text-[11px]"
                    disabled={!selectedCount || deleting}
                    onClick={() => setConfirmBulk(true)}
                  >
                    Eliminar seleccionadas
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pt-1">
          {historyTab === "sesiones" && sessions.length === 0 && (
            <p className="px-1 py-4 text-xs text-muted-foreground">Sin conversaciones.</p>
          )}
          {historyTab === "sesiones" &&
            sessions.map((s) => (
              <div
                key={s.id}
                className={cn(
                  "rounded-xl px-2 py-1.5 text-left text-xs hover:bg-muted",
                  sessionId === s.id && !selectionMode ? "bg-muted font-medium" : "",
                  selectedIds.has(s.id) ? "ring-1 ring-primary/40 bg-primary/5" : "",
                )}
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
                  <div className="flex items-start gap-2">
                    {selectionMode && (
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 shrink-0 accent-primary"
                        checked={selectedIds.has(s.id)}
                        onChange={() => {
                          setSelectedIds((prev) => {
                            const next = new Set(prev);
                            if (next.has(s.id)) next.delete(s.id);
                            else next.add(s.id);
                            return next;
                          });
                        }}
                        aria-label={`Seleccionar ${s.title || "conversación"}`}
                        onClick={(e) => e.stopPropagation()}
                      />
                    )}
                    <div className="min-w-0 flex-1">
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
                      {!selectionMode && (
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
                      )}
                    </div>
                  </div>
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
  );

  return (
    <AppShell title="Lottery IA" description="Plataforma de análisis inteligente">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Link className="shrink-0 text-primary underline-offset-2 hover:underline" href="/lottery">
            Inicio
          </Link>
          <span className="hidden text-muted-foreground sm:inline">/</span>
          <span className="truncate font-medium">Chat inteligente</span>
        </div>
        <p className="hidden max-w-xl text-[11px] text-muted-foreground md:block">{DISCLAIMER}</p>
      </div>

      <div className="relative flex min-h-0 flex-col gap-3 overflow-x-hidden pb-[max(1.5rem,env(safe-area-inset-bottom))] lg:grid lg:grid-cols-[minmax(240px,280px)_minmax(0,1fr)] lg:gap-4">
        {/* Desktop / laptop sidebar */}
        <div className="hidden h-[min(78vh,820px)] lg:block">{historyPanel}</div>

        {/* Mobile / tablet drawer */}
        {historyOpen && (
          <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
            <button
              type="button"
              className="absolute inset-0 bg-black/40"
              aria-label="Cerrar panel"
              onClick={() => setHistoryOpen(false)}
            />
            <div className="absolute inset-y-0 left-0 flex w-[min(100%,22rem)] max-w-full flex-col bg-background p-3 shadow-xl">
              <div className="min-h-0 flex-1">{historyPanel}</div>
            </div>
          </div>
        )}

        <div className="flex min-h-[min(78vh,820px)] flex-col overflow-hidden rounded-2xl border border-border/60 bg-background shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="lg:hidden"
                onClick={() => setHistoryOpen(true)}
              >
                Conversaciones
                {sessions.length ? ` (${sessions.length})` : ""}
              </Button>
              <p className="truncate text-xs text-muted-foreground">
                {sessionId
                  ? sessions.find((s) => s.id === sessionId)?.title || "Conversación"
                  : "Nueva consulta"}
              </p>
            </div>
            <div className="relative">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="sm:hidden"
                onClick={() => setMoreOpen((v) => !v)}
              >
                Más
              </Button>
              {moreOpen && (
                <div className="absolute right-0 z-20 mt-1 w-44 rounded-xl border bg-background p-1 shadow-lg sm:hidden">
                  <button
                    type="button"
                    className="block w-full rounded-lg px-3 py-2 text-left text-xs hover:bg-muted"
                    onClick={() => {
                      setMoreOpen(false);
                      void startSession();
                    }}
                  >
                    Nueva conversación
                  </button>
                  <button
                    type="button"
                    className="block w-full rounded-lg px-3 py-2 text-left text-xs hover:bg-muted"
                    disabled={!sessionId}
                    onClick={() => {
                      setMoreOpen(false);
                      void clearContext();
                    }}
                  >
                    Limpiar contexto
                  </button>
                </div>
              )}
            </div>
          </div>

          {contextLabel && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-muted/15 px-3 py-2 text-[11px]">
              <div className="min-w-0 space-y-0.5 text-muted-foreground">
                <p className="truncate">
                  <span className="font-medium text-foreground/80">Investigación:</span>{" "}
                  {contextLabel.analyzing || "—"}
                </p>
                {contextLabel.filters && (
                  <p className="truncate text-[10px] text-muted-foreground/80">
                    {contextLabel.filters}
                  </p>
                )}
                {contextLabel.primary != null && (
                  <p>
                    <span className="font-medium text-foreground/80">Candidato actual:</span>{" "}
                    {contextLabel.primary}
                  </p>
                )}
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="hidden sm:inline-flex"
                disabled={!sessionId || loading}
                onClick={() => void clearContext()}
              >
                Limpiar contexto
              </Button>
            </div>
          )}

          {error && (
            <div className="mx-3 mt-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          )}
          {success && (
            <div className="mx-3 mt-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 dark:border-emerald-900/40 dark:bg-emerald-950/40 dark:text-emerald-100">
              {success}
            </div>
          )}
          {deleting && (
            <div className="mx-3 mt-2 rounded-xl border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
              Eliminando…
            </div>
          )}

          <div className="relative min-h-0 flex-1">
            <div
              ref={scrollRef}
              onScroll={onScrollPane}
              className="absolute inset-0 overflow-x-hidden overflow-y-auto px-3 py-3 sm:px-4"
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
                  className={cn(
                    "mb-4 flex",
                    m.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {m.role === "user" ? (
                    <div className="max-w-[min(100%,420px)] rounded-2xl bg-primary px-3.5 py-2.5 text-sm text-primary-foreground shadow-sm">
                      <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    </div>
                  ) : (
                    <div className="w-full min-w-0 max-w-full overflow-x-hidden">
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

          <div className="shrink-0 space-y-2 border-t bg-background/95 px-3 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] backdrop-blur">
            <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              {suggestions.map((s) => (
                <Button
                  key={s}
                  size="sm"
                  variant="outline"
                  className="shrink-0"
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
                disabled={loading || deleting}
                placeholder="Pregunta a Lottery IA…"
                className="max-h-40 min-h-[44px] flex-1 resize-none rounded-xl border bg-background px-3 py-2.5 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
                onChange={(e) => {
                  setInput(e.target.value);
                  const el = e.target;
                  el.style.height = "auto";
                  el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send(input);
                  }
                }}
              />
              <Button type="submit" className="shrink-0" disabled={loading || deleting || !input.trim()}>
                Analizar
              </Button>
              {sessionId && error && (
                <Button
                  type="button"
                  variant="secondary"
                  className="hidden shrink-0 sm:inline-flex"
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

      {confirmBulk && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border bg-background p-4 shadow-xl">
            <h3 className="text-base font-semibold">Eliminar seleccionadas</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Vas a eliminar {selectedCount} conversación{selectedCount === 1 ? "" : "es"}. Esta
              acción no se puede deshacer.
            </p>
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <Button type="button" variant="outline" disabled={deleting} onClick={() => setConfirmBulk(false)}>
                Cancelar
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={deleting}
                onClick={() => void confirmBulkDelete()}
              >
                Eliminar definitivamente
              </Button>
            </div>
          </div>
        </div>
      )}

      {confirmDeleteAll && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border bg-background p-4 shadow-xl">
            <h3 className="text-base font-semibold">Eliminar todas las conversaciones</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Vas a eliminar {sessions.length} conversación{sessions.length === 1 ? "" : "es"} de tu
              cuenta. No se borran configuraciones, investigaciones del motor ni datos históricos.
              Escribe <span className="font-semibold text-foreground">ELIMINAR</span> para
              confirmar.
            </p>
            <input
              className="mt-3 w-full rounded-xl border bg-background px-3 py-2 text-sm"
              value={deleteAllPhrase}
              onChange={(e) => setDeleteAllPhrase(e.target.value)}
              placeholder="ELIMINAR"
              autoFocus
            />
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={deleting}
                onClick={() => {
                  setConfirmDeleteAll(false);
                  setDeleteAllPhrase("");
                }}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={deleting || deleteAllPhrase.trim().toUpperCase() !== "ELIMINAR"}
                onClick={() => void confirmDeleteAllSessions()}
              >
                Eliminar todas
              </Button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
