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
  const [statusMessage, setStatusMessage] = useState(
    enabled ? "Analizando histórico…" : "",
  );
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
      try {
        setStatusMessage("Buscando coincidencias Odoo…");
        const result = await apiClient.bootstrapDGCPExpedienteContext(opportunityId, { refresh });
        setHistoricalStatus(result.historical_status);
        setHistoricalMessage(result.historical_message ?? null);
        setHistorical(result.historical ?? null);
        setCommercialStatus(result.commercial_status);
        setCommercialMessage(result.commercial_message ?? null);
        setCommercial(
          normalizeDGCPCommercialContextPayload(result.commercial ?? null),
        );
        setLastUpdated(result.bootstrap_at ?? null);

        const hasError =
          result.historical_status === "error" && result.commercial_status === "error";
        if (hasError) {
          setPhase("error");
          setErrorMessage(result.error_message ?? "Error consultando histórico");
          setStatusMessage("Error consultando histórico");
        } else {
          setPhase("ready");
          setStatusMessage(
            result.historical_status === "timeout"
              ? "Histórico: tiempo agotado — use Reanalizar histórico"
              : result.historical_status === "partial"
                ? "Histórico incompleto — resultado parcial disponible"
                : result.historical_status === "loading" || result.historical_status === "pending"
                  ? "Histórico en proceso…"
                  : "",
          );
        }
      } catch {
        setPhase("error");
        setErrorMessage("Error consultando histórico");
        setStatusMessage("Error consultando histórico");
      } finally {
        setLoading(false);
      }
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
  if (!ctx?.enabled || ctx.phase === "ready" || ctx.phase === "idle") return null;

  const tone =
    ctx.phase === "error"
      ? "border-destructive/40 bg-destructive/5 text-destructive"
      : "border-primary/25 bg-primary/5 text-muted-foreground";

  return (
    <div className={`rounded-lg border px-3 py-2 text-sm ${tone}`}>
      {ctx.phase === "loading" ? ctx.statusMessage || "Analizando histórico…" : ctx.errorMessage}
      {ctx.lastUpdated && ctx.phase === "ready" && (
        <span className="ml-2 text-xs">Última actualización: {ctx.lastUpdated}</span>
      )}
    </div>
  );
}
