"use client";

import { ChevronDown, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import type {
  WhatsappAiActionResponse,
  WhatsappChat,
  WhatsappContextPreview,
  WhatsappDeepContext,
} from "@/lib/communications";
import { cn } from "@/lib/utils";

const SECONDARY_ACTIONS: [string, string][] = [
  ["reply", "Generar respuesta"],
  ["summarize", "Resumir conversación"],
  ["analyze", "Analizar conversación"],
  ["search_mail", "Buscar correos"],
  ["search_docs", "Buscar documentos"],
  ["search_prices", "Buscar precios"],
  ["create_opportunity", "Crear oportunidad"],
  ["create_client", "Crear cliente"],
  ["create_task", "Crear tarea"],
];

type Props = {
  sessionId: string | null;
  chat: WhatsappChat | null;
  onUseReply: (text: string) => void;
};

export function WhatsappAiAssistantPanel({ sessionId, chat, onUseReply }: Props) {
  const [preview, setPreview] = useState<WhatsappContextPreview | null>(null);
  const [deep, setDeep] = useState<WhatsappDeepContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [deepLoading, setDeepLoading] = useState(false);
  const [showConsent, setShowConsent] = useState(false);
  const [actionsOpen, setActionsOpen] = useState(false);
  const [actionResult, setActionResult] = useState<WhatsappAiActionResponse | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadPreview = useCallback(async () => {
    if (!chat) {
      setPreview(null);
      setDeep(null);
      return;
    }
    setLoading(true);
    try {
      const p = await apiClient.getWhatsappContextPreview(chat.id);
      setPreview(p);
      setDeep(null);
      setShowConsent(false);
    } catch {
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }, [chat]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  const runDeepSearch = async () => {
    if (!chat) return;
    setDeepLoading(true);
    setShowConsent(false);
    try {
      const result = await apiClient.whatsappDeepContextSearch(chat.id);
      setDeep(result);
    } finally {
      setDeepLoading(false);
    }
  };

  const runAction = async (action: string) => {
    if (!sessionId || !chat) return;
    setActionLoading(true);
    try {
      const res = await apiClient.whatsappAiAction(sessionId, { action, chat_id: chat.id });
      setActionResult(res);
      if (res.suggested_reply) onUseReply(res.suggested_reply);
    } finally {
      setActionLoading(false);
    }
  };

  if (!chat) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
        Selecciona una conversación para ver el asistente contextual.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-amber-600" />
          <h4 className="text-sm font-semibold">Asistente JAIOS</h4>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4 text-sm">
        {loading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-4 animate-pulse rounded bg-muted" />
            ))}
          </div>
        )}

        {!loading && preview && (
          <>
            <section className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Contacto</p>
              <p className="font-medium">{preview.contact_name}</p>
              {preview.phone_number && (
                <p className="text-xs text-muted-foreground">{preview.phone_number}</p>
              )}
              {preview.company_name && (
                <p className="text-xs text-muted-foreground">Empresa: {preview.company_name}</p>
              )}
              {preview.classification_label && (
                <span className="inline-block rounded-full bg-muted px-2 py-0.5 text-[10px]">
                  {preview.classification_label}
                </span>
              )}
            </section>

            {preview.summary && (
              <section>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Resumen</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{preview.summary}</p>
              </section>
            )}

            {preview.suggested_reply && (
              <section className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                <p className="mb-1 text-[10px] font-semibold uppercase text-emerald-700">Respuesta sugerida</p>
                <p className="text-xs">{preview.suggested_reply}</p>
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-2 h-7 text-xs"
                  onClick={() => onUseReply(preview.suggested_reply || "")}
                >
                  Usar en chat
                </Button>
              </section>
            )}

            {preview.recommendations.length > 0 && (
              <section>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Recomendaciones
                </p>
                <ul className="list-inside list-disc space-y-1 text-xs text-muted-foreground">
                  {preview.recommendations.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </section>
            )}

            {!deep && !showConsent && preview.deep_search_available && (
              <Button
                variant="outline"
                size="sm"
                className="w-full text-xs"
                onClick={() => setShowConsent(true)}
              >
                Buscar información relacionada
              </Button>
            )}

            {showConsent && (
              <div className="rounded-xl border bg-muted/30 p-3 text-xs leading-relaxed">
                <p>
                  Esta solicitud puede beneficiarse de revisar información relacionada en conversaciones previas,
                  correos, documentos, cotizaciones y listas de precios. ¿Deseas que JAIOS busque esa información
                  para ayudarte a responder mejor?
                </p>
                <div className="mt-3 flex flex-col gap-2">
                  <Button size="sm" className="h-8 text-xs" disabled={deepLoading} onClick={runDeepSearch}>
                    Sí, buscar información relacionada
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowConsent(false)}>
                    No, solo usar esta conversación
                  </Button>
                </div>
              </div>
            )}

            {deepLoading && (
              <p className="text-xs text-muted-foreground">Buscando contexto en fuentes internas…</p>
            )}

            {deep && (
              <section className="space-y-3 rounded-xl border p-3">
                <p className="text-xs font-semibold">Contexto ampliado</p>
                {deep.summary && <p className="text-xs text-muted-foreground">{deep.summary}</p>}
                {deep.sales.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium uppercase text-muted-foreground">Ventas</p>
                    {deep.sales.slice(0, 3).map((s, i) => (
                      <p key={i} className="text-xs">{String(s.title || s.product || JSON.stringify(s))}</p>
                    ))}
                  </div>
                )}
                {deep.prices.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium uppercase text-muted-foreground">Precios</p>
                    {deep.prices.slice(0, 4).map((p, i) => (
                      <p key={i} className="text-xs">
                        {String(p.product || p.title)} — {String(p.price || "")} {String(p.supplier || "")}
                      </p>
                    ))}
                  </div>
                )}
                {deep.recommendation && (
                  <p className="rounded-lg bg-amber-500/10 p-2 text-xs">{deep.recommendation}</p>
                )}
              </section>
            )}
          </>
        )}

        {actionResult && (
          <section className="rounded-xl border p-3 text-xs whitespace-pre-wrap">{actionResult.result}</section>
        )}
      </div>

      <div className="border-t p-3">
        <button
          type="button"
          className="flex w-full items-center justify-between text-xs font-medium text-muted-foreground"
          onClick={() => setActionsOpen((v) => !v)}
        >
          Acciones del asistente
          <ChevronDown className={cn("h-4 w-4 transition", actionsOpen && "rotate-180")} />
        </button>
        {actionsOpen && (
          <div className="mt-2 grid gap-1">
            {SECONDARY_ACTIONS.map(([action, label]) => (
              <Button
                key={action}
                variant="ghost"
                size="sm"
                className="h-8 justify-start text-xs"
                disabled={actionLoading}
                onClick={() => runAction(action)}
              >
                {label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
