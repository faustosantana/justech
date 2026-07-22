"use client";

import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ClipboardList,
  Download,
  Loader2,
  RefreshCw,
  Sparkles,
  UserCheck,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type {
  DGCPOfferPreparationAutoAction,
  DGCPOfferPreparationCenterResponse,
} from "@/lib/dgcp";
import { formatCurrency, formatDate } from "@/lib/dgcp";
import { dgcpOfferPreparationCenterEnabled } from "@/lib/dgcp-feature-flags";
import { cn } from "@/lib/utils";

type Props = {
  opportunityId: string;
  onRefreshExpediente?: () => void;
  onGoToAutofill?: (formType?: string) => void;
  onGoToOfferTechnical?: () => void;
  onGoToFichas?: () => void;
};

const AREA_STATUS_COLORS: Record<string, string> = {
  listo: "text-emerald-600",
  parcial: "text-amber-600",
  pendiente: "text-muted-foreground",
  bloqueado: "text-destructive",
};

const RISK_COLORS: Record<string, string> = {
  alto: "border-destructive/40 bg-destructive/5",
  high: "border-destructive/40 bg-destructive/5",
  medio: "border-amber-500/40 bg-amber-500/5",
  medium: "border-amber-500/40 bg-amber-500/5",
  bajo: "border-muted bg-muted/30",
  low: "border-muted bg-muted/30",
};

export function DgcpOfferPreparationCenter({
  opportunityId,
  onRefreshExpediente,
  onGoToAutofill,
  onGoToOfferTechnical,
  onGoToFichas,
}: Props) {
  const enabled = dgcpOfferPreparationCenterEnabled();
  const [data, setData] = useState<DGCPOfferPreparationCenterResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [consolidatedPreview, setConsolidatedPreview] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPOfferPreparationCenter(opportunityId);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el estado de la oferta.");
    } finally {
      setLoading(false);
    }
  }, [enabled, opportunityId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runAction(action: DGCPOfferPreparationAutoAction) {
    setBusy(action.id);
    setError(null);
    try {
      const p = action.payload || {};
      switch (action.action_type) {
        case "generate_form":
          onGoToAutofill?.(typeof p.form_type === "string" ? p.form_type : undefined);
          break;
        case "generate_technical_sheet":
          onGoToFichas?.();
          break;
        case "run_compliance_matrix":
        case "run_technical_intelligence":
          onGoToOfferTechnical?.();
          if (action.action_type === "run_technical_intelligence") {
            await apiClient.runDGCPProductIntelligence(opportunityId, false);
          } else if (typeof p.requirement_id === "string" && typeof p.candidate_id === "string") {
            await apiClient.buildDGCPComplianceMatrix(opportunityId, p.requirement_id, p.candidate_id);
          } else {
            await apiClient.runDGCPProductIntelligence(opportunityId, false);
          }
          break;
        case "generate_consolidated_offer": {
          const res = await apiClient.generateDGCPConsolidatedTechnicalOffer(opportunityId);
          setConsolidatedPreview(res.content);
          break;
        }
        case "prepare_expediente":
          onRefreshExpediente?.();
          break;
        default:
          break;
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo ejecutar la acción.");
    } finally {
      setBusy(null);
    }
  }

  function downloadConsolidated() {
    if (!consolidatedPreview || !data?.consolidated_offer.filename) return;
    const blob = new Blob([consolidatedPreview], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.consolidated_offer.filename || "oferta_tecnica_consolidada.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!enabled) return null;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
        <Loader2 className="h-4 w-4 animate-spin" /> Cargando estado de la oferta…
      </div>
    );
  }

  if (!data) return null;

  const exec = data.executive_summary;

  return (
    <Card className="border-primary/30 bg-primary/[0.02]">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Estado general de la oferta
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Centro de preparación del expediente — qué está listo, qué falta y qué puede generar JAIOS.
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => void load()} disabled={!!busy}>
            <RefreshCw className={cn("h-3.5 w-3.5 mr-1", busy && "animate-spin")} />
            Actualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {error && (
          <p className="text-xs text-destructive border border-destructive/30 rounded p-2 bg-destructive/5">{error}</p>
        )}

        {/* Resumen ejecutivo */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <InfoField label="Institución" value={exec.institution} />
          <InfoField label="Proceso" value={exec.process_code} />
          <InfoField label="Modalidad" value={exec.modalidad ?? "—"} />
          <InfoField label="Fecha límite" value={exec.deadline ? formatDate(exec.deadline) : "—"} />
          <InfoField
            label="Monto estimado"
            value={exec.estimated_amount != null ? formatCurrency(exec.estimated_amount, exec.currency) : "—"}
          />
          <InfoField label="Garantía" value={exec.guarantee_amount ?? "—"} />
          <InfoField label="Empresa" value={exec.participating_company} />
          <InfoField label="Interés" value={exec.interest_status_label} />
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <div>
            <p className="text-[10px] uppercase text-muted-foreground font-medium">Avance por áreas</p>
            <p className="text-3xl font-bold text-primary">{exec.overall_preparation_pct.toFixed(0)}%</p>
          </div>
          <div className="flex-1 min-w-[200px] max-w-md h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${Math.min(100, exec.overall_preparation_pct)}%` }}
            />
          </div>
          <Badge variant="outline">{exec.expediente_status ?? "sin_preparar"}</Badge>
        </div>

        {/* Preparación por área */}
        {data.areas.length > 0 && (
          <div>
            <p className="text-xs font-medium mb-2 flex items-center gap-1">
              <ClipboardList className="h-3.5 w-3.5" /> Preparación por área
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {data.areas.map((area) => (
                <div key={area.key} className="rounded border p-2">
                  <div className="flex justify-between items-center gap-1">
                    <span className="text-[11px] font-medium truncate">{area.label}</span>
                    <span className={cn("text-sm font-bold", AREA_STATUS_COLORS[area.status] ?? "")}>
                      {area.preparation_pct != null ? `${area.preparation_pct}%` : "—"}
                    </span>
                  </div>
                  {area.detail && (
                    <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2">{area.detail}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Branding corporativo */}
        {(data.branding_status?.length ?? 0) > 0 && (
          <div>
            <p className="text-xs font-medium mb-2">Identidad corporativa</p>
            <div className="flex flex-wrap gap-2">
              {data.branding_status.map((asset) => (
                <Badge
                  key={asset.asset_type}
                  variant={asset.status === "detectado" ? "secondary" : "outline"}
                  className={cn(
                    "text-[10px]",
                    asset.status === "falta" && "border-amber-500/40 text-amber-800",
                  )}
                >
                  {asset.label}: {asset.status === "detectado" ? "Detectado" : asset.status === "falta" ? "Falta" : "Requiere actualización"}
                </Badge>
              ))}
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-4">
          {/* Pendientes críticos */}
          <PendingBlock
            title="Pendientes críticos"
            icon={<AlertTriangle className="h-3.5 w-3.5 text-destructive" />}
            items={data.critical_pending}
            empty="Ningún bloqueo crítico detectado."
            variant="critical"
          />
          <PendingBlock
            title="Pendientes menores"
            icon={<CheckCircle2 className="h-3.5 w-3.5 text-muted-foreground" />}
            items={data.minor_pending}
            empty="Sin pendientes menores."
            variant="minor"
          />
        </div>

        {/* Acciones automáticas */}
        {data.auto_actions.length > 0 && (
          <div>
            <p className="text-xs font-medium mb-2 flex items-center gap-1">
              <Zap className="h-3.5 w-3.5" /> Acciones automáticas disponibles
            </p>
            <div className="flex flex-wrap gap-2">
              {data.auto_actions.map((action) => (
                <Button
                  key={action.id}
                  size="sm"
                  variant="secondary"
                  className="h-7 text-[10px]"
                  disabled={!!busy || !action.enabled}
                  onClick={() => void runAction(action)}
                >
                  {busy === action.id ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : null}
                  {action.label}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Decisiones humanas */}
        {data.human_decisions.length > 0 && (
          <div>
            <p className="text-xs font-medium mb-2 flex items-center gap-1">
              <UserCheck className="h-3.5 w-3.5" /> Decisiones humanas pendientes
            </p>
            <ul className="space-y-1 text-xs">
              {data.human_decisions.map((d) => (
                <li key={d.id} className="rounded border border-amber-500/30 bg-amber-500/5 px-2 py-1.5">
                  <span className="font-medium">{d.label}</span>
                  {d.reason && <span className="text-muted-foreground"> — {d.reason}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Riesgos */}
        {data.risks.length > 0 && (
          <div>
            <p className="text-xs font-medium mb-2 flex items-center gap-1">
              <Bot className="h-3.5 w-3.5" /> Riesgos del proceso (Hermes + análisis)
            </p>
            <ul className="space-y-1.5">
              {data.risks.slice(0, 8).map((r, i) => (
                <li
                  key={`${r.descripcion}-${i}`}
                  className={cn("rounded border px-2 py-1.5 text-xs", RISK_COLORS[r.nivel.toLowerCase()] ?? "")}
                >
                  <Badge variant="outline" className="text-[9px] mr-1 uppercase">{r.nivel}</Badge>
                  {r.descripcion}
                  {r.fuente && <span className="text-muted-foreground"> · {r.fuente}</span>}
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Evidencia: {r.evidencia || "Evidencia no disponible"}
                    {r.documento_origen ? ` · Origen: ${r.documento_origen}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Oferta técnica consolidada */}
        <div className="rounded border p-3 space-y-2">
          <p className="text-xs font-medium">Oferta técnica consolidada</p>
          <p className="text-[10px] text-muted-foreground">
            Documento único estructurado en estado{" "}
            <Badge variant="secondary" className="text-[9px]">
              {data.consolidated_offer.status === "sin_generar" ? "BORRADOR (sin generar)" : data.consolidated_offer.status.toUpperCase()}
            </Badge>
            — requiere aprobación humana antes de presentar.
          </p>
          {data.consolidated_offer.sections.length > 0 && (
            <p className="text-[10px] text-muted-foreground">
              Secciones: {data.consolidated_offer.sections.join(" · ")}
            </p>
          )}
          {(consolidatedPreview || data.consolidated_offer.preview_excerpt) && (
            <pre className="text-[10px] bg-muted/40 rounded p-2 max-h-40 overflow-auto whitespace-pre-wrap">
              {consolidatedPreview ?? data.consolidated_offer.preview_excerpt}
            </pre>
          )}
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-[10px]"
              disabled={!!busy}
              onClick={() => void runAction({
                id: "gen-consolidated-btn",
                label: "Generar",
                action_type: "generate_consolidated_offer",
                area: "oferta_tecnica",
                enabled: true,
                payload: {},
              })}
            >
              Generar borrador consolidado
            </Button>
            {(consolidatedPreview || data.consolidated_offer.status === "borrador") && (
              <Button size="sm" variant="ghost" className="h-7 text-[10px]" onClick={downloadConsolidated}>
                <Download className="h-3 w-3 mr-1" /> Descargar .md
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="font-medium truncate" title={value}>{value}</p>
    </div>
  );
}

function PendingBlock({
  title,
  icon,
  items,
  empty,
  variant,
}: {
  title: string;
  icon: React.ReactNode;
  items: DGCPOfferPreparationCenterResponse["critical_pending"];
  empty: string;
  variant: "critical" | "minor";
}) {
  return (
    <div className={cn("rounded border p-3", variant === "critical" ? "border-destructive/20" : "")}>
      <p className="text-xs font-medium mb-2 flex items-center gap-1">{icon} {title}</p>
      {items.length === 0 ? (
        <p className="text-[10px] text-muted-foreground">{empty}</p>
      ) : (
        <ul className="space-y-1 max-h-48 overflow-auto">
          {items.map((item) => (
            <li key={item.id} className="text-[11px] border-b border-border/50 pb-1 last:border-0">
              <span className="font-medium">{item.label}</span>
              {item.reason && <p className="text-muted-foreground text-[10px]">{item.reason}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
