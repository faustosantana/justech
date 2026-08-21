"use client";

import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock,
  Loader2,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { DGCPProcessUpdateRecord, DGCPProcessUpdatesResponse } from "@/lib/dgcp";
import { dgcpProcessUpdatesEnabled } from "@/lib/dgcp-feature-flags";
import { cn } from "@/lib/utils";

const CHANGE_TYPE_LABELS: Record<string, string> = {
  estado_cambiado: "Cambio de estado",
  enmienda: "Enmienda",
  circular: "Circular",
  respuesta_preguntas: "Respuesta a preguntas",
  documento_nuevo: "Documento nuevo",
  documento_reemplazado: "Documento reemplazado",
  fecha_cambiada: "Cambio de fecha",
  cronograma_cambiado: "Cronograma",
  pliego_modificado: "Pliego / TDR",
  adjudicacion: "Adjudicación",
  cancelacion: "Cancelación",
  suspension: "Suspensión",
  extension_plazo: "Extensión de plazo",
  otro: "Otro",
};

const IMPACT_COLORS: Record<string, string> = {
  critico: "border-destructive/40 bg-destructive/5 text-destructive",
  requiere_revision: "border-amber-500/40 bg-amber-500/5 text-amber-800",
  informativo: "border-muted bg-muted/30 text-muted-foreground",
};

const SUGGESTION_LABELS: Record<string, string> = {
  reanalyze_hermes: "Reanalizar Hermes",
  update_checklist: "Actualizar checklist",
  review_technical_sheets: "Revisar fichas técnicas",
  review_compliance_matrix: "Revisar matriz de cumplimiento",
};

type Props = {
  opportunityId: string;
  onPendingCountChange?: (count: number) => void;
};

export function DgcpProcessUpdatesPanel({ opportunityId, onPendingCountChange }: Props) {
  const enabled = dgcpProcessUpdatesEnabled();
  const [data, setData] = useState<DGCPProcessUpdatesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPProcessUpdates(opportunityId);
      setData(res);
      onPendingCountChange?.(res.meta?.pending_count ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las actualizaciones.");
    } finally {
      setLoading(false);
    }
  }, [enabled, opportunityId, onPendingCountChange]);

  useEffect(() => {
    void load();
  }, [load]);

  async function checkNow() {
    setBusy("check");
    try {
      const res = await apiClient.checkDGCPProcessUpdates(opportunityId);
      setData(res);
      onPendingCountChange?.(res.meta?.pending_count ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al verificar portal.");
    } finally {
      setBusy(null);
    }
  }

  async function markReviewed(update: DGCPProcessUpdateRecord) {
    setBusy(update.id);
    try {
      await apiClient.markDGCPProcessUpdateReviewed(opportunityId, update.id);
      await load();
    } finally {
      setBusy(null);
    }
  }

  async function markApplied(update: DGCPProcessUpdateRecord) {
    setBusy(update.id);
    try {
      await apiClient.markDGCPProcessUpdateApplied(opportunityId, update.id);
      await load();
    } finally {
      setBusy(null);
    }
  }

  if (!enabled) return null;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
        <Loader2 className="h-4 w-4 animate-spin" /> Cargando actualizaciones del proceso…
      </div>
    );
  }

  if (!data) return null;

  return (
    <Card className="border-amber-500/30 bg-amber-500/[0.02]">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Bell className="h-4 w-4 text-amber-600" />
              Actualizaciones del proceso
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Cambios detectados en portal DGCP — historial auditado, sin modificaciones automáticas.
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => void checkNow()} disabled={!!busy}>
            <RefreshCw className={cn("h-3.5 w-3.5 mr-1", busy === "check" && "animate-spin")} />
            Verificar portal
          </Button>
        </div>
        {data.meta.requires_reanalysis && (
          <div className="mt-2 rounded border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs flex items-center gap-2 text-destructive">
            <ShieldAlert className="h-4 w-4 shrink-0" />
            Expediente marcado como <strong>requiere reanálisis</strong> — confirme acciones manualmente.
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <p className="text-xs text-destructive">{error}</p>}

        {data.updates.length === 0 ? (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">Sin cambios registrados desde el último snapshot del portal.</p>
            <Button size="sm" variant="outline" onClick={() => void checkNow()} disabled={!!busy}>
              <RefreshCw className={cn("h-3.5 w-3.5 mr-1", busy === "check" && "animate-spin")} />
              Verificar portal ahora
            </Button>
          </div>
        ) : (
          <ul className="space-y-2">
            {data.updates.slice().reverse().map((update) => (
              <li key={update.id} className="rounded border p-3 text-xs space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="text-[9px]">
                    {CHANGE_TYPE_LABELS[update.change_type] ?? update.change_type}
                  </Badge>
                  <Badge className={cn("text-[9px] uppercase", IMPACT_COLORS[update.impact] ?? "")}>
                    {update.impact.replace("_", " ")}
                  </Badge>
                  <Badge variant="secondary" className="text-[9px]">
                    {update.review_status}
                  </Badge>
                  <span className="text-muted-foreground flex items-center gap-1 ml-auto">
                    <Clock className="h-3 w-3" />
                    {new Date(update.detected_at).toLocaleString("es-DO")}
                  </span>
                </div>
                <p className="font-medium">{update.description}</p>
                {update.affected_document && (
                  <p className="text-muted-foreground">Documento: {update.affected_document}</p>
                )}
                <p className="text-muted-foreground">{update.recommended_action}</p>
                {update.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {update.suggestions.map((s) => (
                      <Badge key={s} variant="outline" className="text-[9px]">
                        {SUGGESTION_LABELS[s] ?? s}
                      </Badge>
                    ))}
                  </div>
                )}
                {update.review_status === "pendiente" && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="h-7 text-[10px]"
                      disabled={!!busy}
                      onClick={() => void markReviewed(update)}
                    >
                      {busy === update.id ? (
                        <Loader2 className="h-3 w-3 animate-spin mr-1" />
                      ) : (
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                      )}
                      Marcar revisado
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-[10px]"
                      disabled={!!busy}
                      onClick={() => void markApplied(update)}
                    >
                      Marcar aplicado
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        {data.meta.pending_count > 0 && (
          <p className="text-[10px] text-muted-foreground flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            {data.meta.pending_count} pendiente(s) · {data.meta.critical_count} crítico(s)
          </p>
        )}
      </CardContent>
    </Card>
  );
}
