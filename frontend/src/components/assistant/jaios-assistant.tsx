"use client";

import { Maximize2, Minimize2, Send, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { CopilotExecutivePanel } from "@/components/assistant/copilot-executive-panel";
import {
  loadBriefingMode,
  saveBriefingMode,
  type BriefingMode,
} from "@/components/assistant/copilot-mode-selector";
import { AssistantActionButtons } from "@/components/assistant/assistant-action-buttons";
import { AssistantAvatar } from "@/components/assistant/assistant-avatar";
import { AssistantStructuredResponse } from "@/components/assistant/assistant-structured-response";
import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  isStructuredAnswer,
  loadAssistantHistory,
  saveAssistantHistory,
  sourceBadgeColor,
  type AssistantMessage,
  type CopilotBriefingResponse,
  type QuickViewTarget,
} from "@/lib/assistant";
import { AssistantQuickViewModal } from "@/components/assistant/assistant-quick-view-modal";
import {
  getConversationId,
  getProactivePrompt,
  isAssistantDebugEnabled,
} from "@/lib/assistant-proactive";
import { cn } from "@/lib/utils";

interface JaiosAssistantProps {
  companyContextId?: number | null;
  recordType?: string | null;
  recordId?: string | null;
  presetQuestion?: string | null;
  contextLabel?: string;
  companyScopeLabel?: string;
  onClearRecordContext?: () => void;
  controlledOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  proactiveBriefing?: string | null;
}

export function JaiosAssistant({
  companyContextId,
  recordType,
  recordId,
  presetQuestion,
  contextLabel = "JAIOS",
  companyScopeLabel,
  onClearRecordContext,
  controlledOpen,
  onOpenChange,
  proactiveBriefing,
}: JaiosAssistantProps) {
  const pathname = usePathname();
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = useCallback(
    (value: boolean) => {
      if (onOpenChange) onOpenChange(value);
      else setInternalOpen(value);
    },
    [onOpenChange],
  );
  const [fullscreen, setFullscreen] = useState(false);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [quickView, setQuickView] = useState<QuickViewTarget | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [briefing, setBriefing] = useState<CopilotBriefingResponse | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [briefingMode, setBriefingMode] = useState<BriefingMode>("managerial");
  const bottomRef = useRef<HTMLDivElement>(null);
  const proactive = getProactivePrompt(pathname);

  useEffect(() => {
    setShowDebug(isAssistantDebugEnabled());
  }, []);

  useEffect(() => {
    setMessages(loadAssistantHistory());
  }, []);

  useEffect(() => {
    if (presetQuestion) {
      setQuestion(presetQuestion);
      setOpen(true);
    }
  }, [presetQuestion, setOpen]);

  useEffect(() => {
    if (controlledOpen === true) {
      setFullscreen(false);
    }
  }, [controlledOpen]);

  useEffect(() => {
    setBriefingMode(loadBriefingMode());
  }, []);

  useEffect(() => {
    if (!open || messages.length > 0 || !getAccessToken()) return;
    setBriefingLoading(true);
    void apiClient
      .getAssistantBriefing(briefingMode)
      .then(setBriefing)
      .catch(() => setBriefing(null))
      .finally(() => setBriefingLoading(false));
  }, [open, messages.length, briefingMode]);

  const handleBriefingModeChange = useCallback((mode: BriefingMode) => {
    setBriefingMode(mode);
    saveBriefingMode(mode);
    const convId = getConversationId();
    void apiClient.setAssistantBriefingMode(convId, mode).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open, loading]);

  const closeAssistant = useCallback(() => {
    setOpen(false);
    setFullscreen(false);
    setQuickView(null);
  }, [setOpen]);

  const ask = useCallback(async (overrideQuestion?: string) => {
    const q = (overrideQuestion ?? question).trim();
    if (!q || loading) return;
    if (!getAccessToken()) {
      window.location.href = "/login?session=expired";
      return;
    }
    const userMsg: AssistantMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: q,
      timestamp: Date.now(),
    };
    const next = [...messages, userMsg];
    setMessages(next);
    setQuestion("");
    setLoading(true);
    try {
      const res = await apiClient.assistantQuery({
        question: q,
        current_module: pathname,
        current_company_context: companyContextId ?? undefined,
        current_record_id: recordId ?? undefined,
        record_type: recordType ?? undefined,
        conversation_id: getConversationId(),
        debug_context: showDebug,
      });
      const assistantMsg: AssistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer,
        response: res,
        timestamp: Date.now(),
      };
      const updated = [...next, assistantMsg];
      setMessages(updated);
      saveAssistantHistory(updated);
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        return;
      }
      const message =
        err instanceof ApiError
          ? err.message
          : "No pude procesar la consulta. Verifica que el backend esté activo o intenta de nuevo en unos segundos.";
      const errMsg: AssistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: message,
        timestamp: Date.now(),
      };
      const updated = [...next, errMsg];
      setMessages(updated);
      saveAssistantHistory(updated);
    } finally {
      setLoading(false);
    }
  }, [question, loading, messages, pathname, companyContextId, recordId, recordType, showDebug]);

  const scopeDisplay = (() => {
    const raw = companyScopeLabel || contextLabel;
    if (raw.startsWith("Consultando en:")) return raw;
    return `Consultando en: ${raw}`;
  })();

  if (pathname === "/login") return null;

  const panelClasses = cn(
    "fixed z-50 flex flex-col brand-surface shadow-2xl transition-all duration-300",
    fullscreen
      ? "inset-0 md:left-[4.25rem] md:right-0 md:top-0 md:bottom-0 lg:left-60"
      : "inset-y-0 right-0 w-full max-w-md border-l border-border",
    open ? "translate-x-0 opacity-100" : "translate-x-full opacity-0 pointer-events-none",
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          "assistant-fab fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full pl-2 pr-4 py-2 transition-transform hover:scale-[1.02]",
          open && "scale-0 pointer-events-none",
        )}
        aria-label="Abrir JAIOS Assistant"
      >
        <AssistantAvatar size="sm" state={loading ? "thinking" : proactive.state} animated />
        <span className="hidden text-sm font-medium sm:inline">JAIOS Assistant</span>
      </button>

      <div className={panelClasses} data-testid="assistant-panel" data-open={open ? "true" : "false"}>
        <div className="assistant-panel-header flex shrink-0 items-center justify-between px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <AssistantAvatar size="sm" state={loading ? "thinking" : proactive.state} animated />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">JAIOS Copiloto</p>
              <p className="text-[10px] text-muted-foreground">
                {fullscreen ? "Pantalla completa" : "Copiloto empresarial · solo lectura"}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {fullscreen ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFullscreen(false)}
                title="Volver a panel lateral"
                aria-label="Volver a panel lateral"
              >
                <Minimize2 className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFullscreen(true)}
                title="Pantalla completa"
                aria-label="Pantalla completa"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={closeAssistant} aria-label="Cerrar">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="shrink-0 border-b border-border bg-muted/20 px-4 py-1.5 flex justify-end">
          <button
            type="button"
            className="text-[10px] text-muted-foreground hover:text-primary hover:underline"
            onClick={() => {
              const id = getConversationId();
              void apiClient.resetAssistantConversation(id).catch(() => undefined);
              setMessages([]);
              saveAssistantHistory([]);
            }}
          >
            Nueva conversación
          </button>
        </div>

        <div className="shrink-0 border-b border-border bg-muted/30 px-4 py-2">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-xs text-muted-foreground">
              {scopeDisplay}
              {companyScopeLabel && contextLabel !== companyScopeLabel ? (
                <>
                  {" · "}
                  <span className="font-medium text-foreground">{contextLabel}</span>
                </>
              ) : null}
            </p>
            {(recordType || recordId) && onClearRecordContext && (
              <button
                type="button"
                onClick={onClearRecordContext}
                className="shrink-0 text-[10px] text-primary hover:underline"
              >
                Limpiar contexto
              </button>
            )}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4">
          {messages.length === 0 && (
            <CopilotExecutivePanel
              briefing={proactiveBriefing ? {
                greeting: proactiveBriefing,
                mode: briefingMode,
                priorities: { title: "Prioridades", items: [] },
                alerts: { title: "Alertas", items: [] },
                opportunities: { title: "Oportunidades", items: [] },
                recommendations: { title: "Recomendaciones", items: [] },
                quick_actions: proactive.actions.slice(0, 4).map((a) => ({
                  label: a.label,
                  question: a.question,
                  href: a.href,
                })),
                recent_activity: { title: "Últimas actividades", items: [] },
              } : briefing}
              loading={briefingLoading && !proactiveBriefing}
              mode={briefingMode}
              onModeChange={handleBriefingModeChange}
              onAsk={(q) => void ask(q)}
            />
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={cn(
                "max-w-full rounded-lg px-3 py-2 text-sm",
                m.role === "user"
                  ? fullscreen
                    ? "ml-[20%] bg-primary/10 text-foreground"
                    : "ml-8 bg-primary/10 text-foreground"
                  : fullscreen
                    ? "mr-[5%] bg-muted/50"
                    : "mr-4 bg-muted/50",
              )}
            >
              {!m.response?.structured_data || !isStructuredAnswer(m.response.structured_data) ? (
                <p className="whitespace-pre-wrap break-words">{m.content}</p>
              ) : null}
              {m.response && (
                <div className="mt-2 max-w-full space-y-2 overflow-hidden">
                  {m.response.was_follow_up && m.response.resolved_question && (
                    <p className="text-[10px] text-muted-foreground">
                      Interpreté: «{m.response.resolved_question}»
                    </p>
                  )}
                  {showDebug && m.response.conversation_context && (
                    <pre className="overflow-x-auto rounded-md bg-muted p-2 text-[10px]">
                      {JSON.stringify(m.response.conversation_context, null, 2)}
                    </pre>
                  )}
                  {m.response.structured_data && isStructuredAnswer(m.response.structured_data) && (
                    <AssistantStructuredResponse
                      data={m.response.structured_data}
                      wide={fullscreen}
                      onQuickView={setQuickView}
                      onNavigate={closeAssistant}
                    />
                  )}
                  {m.response.actions && m.response.actions.length > 0 && (
                    <AssistantActionButtons
                      actions={m.response.actions}
                      onQuickView={(entityType, entityId) =>
                        setQuickView({ entity_type: entityType, entity_id: entityId })
                      }
                      onNavigate={closeAssistant}
                    />
                  )}
                  <div className="flex flex-wrap gap-1">
                    {m.response.sources.map((s) => (
                      <span
                        key={s}
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-medium",
                          sourceBadgeColor(s),
                        )}
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                  {!isStructuredAnswer(m.response.structured_data) &&
                    m.response.cards.map((card, i) => (
                      <div
                        key={i}
                        className="rounded-md border border-border bg-background p-2 text-xs"
                      >
                        <p className="break-words font-medium">{card.title}</p>
                        {card.subtitle && (
                          <p className="break-words text-muted-foreground">{card.subtitle}</p>
                        )}
                        <div className="mt-1 grid grid-cols-2 gap-1">
                          {Object.entries(card.fields).map(([k, v]) => (
                            <span key={k} className="break-words">
                              <span className="text-muted-foreground">{k}: </span>
                              {v}
                            </span>
                          ))}
                        </div>
                        {card.link && (
                          <Link
                            href={card.link}
                            className="mt-1 text-primary hover:underline"
                            onClick={closeAssistant}
                          >
                            Ver detalle →
                          </Link>
                        )}
                      </div>
                    ))}
                  {!isStructuredAnswer(m.response.structured_data) &&
                    m.response.links.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {m.response.links.map((lnk, i) =>
                          lnk.url.startsWith("http") ? (
                            <a
                              key={i}
                              href={lnk.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="break-words text-xs text-primary hover:underline"
                            >
                              {lnk.label} ↗
                            </a>
                          ) : (
                            <Link
                              key={i}
                              href={lnk.url}
                              className="break-words text-xs text-primary hover:underline"
                              onClick={closeAssistant}
                            >
                              {lnk.label}
                            </Link>
                          ),
                        )}
                      </div>
                    )}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <p className="text-xs text-muted-foreground animate-pulse">Consultando…</p>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="shrink-0 border-t border-border p-4">
          <div className="flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && ask()}
              placeholder="Escribe o elige una acción del copiloto…"
              className="brand-input min-w-0 flex-1"
            />
            <Button size="sm" onClick={() => void ask()} disabled={loading || !question.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {open && !fullscreen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/20"
          aria-label="Cerrar asistente"
          onClick={closeAssistant}
        />
      )}

      <AssistantQuickViewModal target={quickView} onClose={() => setQuickView(null)} />
    </>
  );
}
