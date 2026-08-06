"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiClient } from "@/lib/api";
import type { DGCPHistoricalSimilarResponse } from "@/lib/dgcp";
import {
  isDgcpAutoExpedienteContextEnabled,
  type DGCPCommercialContextPayload,
  type DGCPExpedienteContextState,
  normalizeDGCPCommercialContextPayload,
} from "@/lib/dgcp-expediente-context";

const DgcpExpedienteContext = createContext<DGCPExpedienteContextState | null>(null);

export function useDgcpExpedienteContext(): DGCPExpedienteContextState | null {
  return useContext(DgcpExpedienteContext);
}

export function DgcpExpedienteContextProvider({
  opportunityId,
  children,
}: {
  opportunityId: string;
  children: ReactNode;
}) {
  const enabled = isDgcpAutoExpedienteContextEnabled();
  const [loading, setLoading] = useState(enabled);
  const [phase, setPhase] = useState<DGCPExpedienteContextState["phase"]>(enabled ? "loading" : "idle");
  const [statusMessage, setStatusMessage] = useState(enabled ? "Analizando histórico…" : "");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [historicalStatus, setHistoricalStatus] = useState("pending");
  const [historicalMessage, setHistoricalMessage] = useState<string | null>(null);
  const [historical, setHistorical] = useState<DGCPHistoricalSimilarResponse | null>(null);
  const [commercialStatus, setCommercialStatus] = useState("pending");
  const [commercialMessage, setCommercialMessage] = useState<string | null>(null);
  const [commercial, setCommercial] = useState<DGCPCommercialContextPayload | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runBootstrap = useCallback(
    async (refresh = false) => {
      if (!enabled) return;
      setLoading(true);
      setPhase("loading");
      setStatusMessage("Analizando histórico…");
      setErrorMessage(null);

      let hist: DGCPHistoricalSimilarResponse | null = null;
      let histStatus = "pending";
      let histMessage: string | null = null;
      let commStatus = "pending";
      let commMessage: string | null = null;
      let comm: DGCPCommercialContextPayload | null = null;
      let bootAt: string | null = null;

      try {
        if (typeof apiClient.bootstrapDGCPExpedienteContext === "function") {
          setStatusMessage("Buscando coincidencias…");
          const result = await apiClient.bootstrapDGCPExpedienteContext(opportunityId, { refresh });
          hist = result.historical ?? null;
          histStatus = result.historical_status || (hist ? "done" : "empty");
          histMessage = result.historical_message ?? null;
          commStatus = result.commercial_status || "done";
          commMessage = result.commercial_message ?? null;
          comm = normalizeDGCPCommercialContextPayload(result.commercial ?? null);
          bootAt = result.bootstrap_at ?? null;
        } else {
          throw new Error("bootstrap_unavailable");
        }
      } catch {
        // Fallback: historical alone must still work; commercial is secondary.
        try {
          setStatusMessage("Consultando adjudicaciones similares…");
          hist = await apiClient.getDGCPHistoricalSimilar(opportunityId);
          histStatus = hist?.matches?.length ? "done" : "empty";
          histMessage = hist?.message ?? null;
          bootAt = new Date().toISOString();
          commStatus = "skipped";
          commMessage = "Integración comercial no disponible en este momento.";
        } catch {
          histStatus = "error";
          histMessage = "No se pudo consultar el histórico de adjudicaciones.";
          commStatus = "skipped";
        }
      }

      // Optional refresh of historical if bootstrap returned empty and refresh requested
      if (refresh && (!hist || !(hist.matches || []).length) && histStatus !== "error") {
        try {
          hist = await apiClient.searchDGCPHistoricalSimilar(opportunityId, { refresh: true, limit: 10 });
          histStatus = hist?.matches?.length ? "done" : "empty";
          histMessage = hist?.message ?? histMessage;
        } catch {
          /* keep prior */
        }
      }

      setHistorical(hist);
      setHistoricalStatus(histStatus);
      setHistoricalMessage(histMessage);
      setCommercialStatus(commStatus);
      setCommercialMessage(commMessage);
      setCommercial(comm);
      setLastUpdated(bootAt);

      const hasMatches = Boolean(hist?.matches?.length);
      const histFailed = histStatus === "error" && !hasMatches;

      if (histFailed) {
        setPhase("error");
        setErrorMessage(histMessage || "Error consultando histórico");
        setStatusMessage(histMessage || "Error consultando histórico");
      } else {
        setPhase("ready");
        setErrorMessage(null);
        setStatusMessage(
          histStatus === "timeout"
            ? "Histórico: tiempo agotado — use Reanalizar histórico"
            : histStatus === "partial"
              ? "Histórico incompleto — resultado parcial disponible"
              : "",
        );
      }
      setLoading(false);
    },
    [enabled, opportunityId],
  );

  useEffect(() => {
    if (!enabled) return;
    void runBootstrap(false);
  }, [enabled, runBootstrap]);

  const value = useMemo<DGCPExpedienteContextState>(
    () => ({
      enabled,
      loading,
      phase,
      statusMessage,
      lastUpdated,
      historicalStatus,
      historicalMessage,
      historical,
      commercialStatus,
      commercialMessage,
      commercial,
      errorMessage,
      refresh: runBootstrap,
    }),
    [
      enabled,
      loading,
      phase,
      statusMessage,
      lastUpdated,
      historicalStatus,
      historicalMessage,
      historical,
      commercialStatus,
      commercialMessage,
      commercial,
      errorMessage,
      runBootstrap,
    ],
  );

  return (
    <DgcpExpedienteContext.Provider value={value}>{children}</DgcpExpedienteContext.Provider>
  );
}

export function ExpedienteContextStatusBanner() {
  const ctx = useDgcpExpedienteContext();
  // Never show error banner when historical data is already available.
  if (!ctx?.enabled) return null;
  if (ctx.phase === "ready" || ctx.phase === "idle") return null;
  if (ctx.phase === "error" && (ctx.historical?.matches?.length || 0) > 0) return null;

  const tone =
    ctx.phase === "error"
      ? "border-destructive/40 bg-destructive/5 text-destructive"
      : "border-primary/25 bg-primary/5 text-muted-foreground";

  return (
    <div className={`rounded-lg border px-3 py-2 text-sm ${tone}`}>
      {ctx.phase === "loading"
        ? ctx.statusMessage || "Analizando histórico…"
        : ctx.errorMessage || "No se encontraron procesos suficientemente similares."}
      {ctx.phase === "error" && (
        <button
          type="button"
          className="ml-3 underline"
          onClick={() => void ctx.refresh(true)}
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
