"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";

type DupItem = {
  status: string;
  reason: string;
  confidence: number;
  auto_merge_allowed?: boolean;
  supplier_a?: { display_name: string; identity_key: string; rpe?: string; awards_count: number };
  supplier_b?: { display_name: string; identity_key: string; rpe?: string; awards_count: number };
  institution_a?: { display_name: string; identity_key: string; code?: string; awards_count: number };
  institution_b?: { display_name: string; identity_key: string; code?: string; awards_count: number };
  rpe_a?: string;
  rpe_b?: string;
  name_norm_a?: string;
  name_norm_b?: string;
};

export default function DgcpDataQualityPage() {
  const [partyType, setPartyType] = useState<"supplier" | "institution">("supplier");
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<DupItem[]>([]);
  const [conservation, setConservation] = useState<Record<string, number> | null>(null);
  const [health, setHealth] = useState<{
    status: string;
    http_status?: number | null;
    message?: string;
    last_successful_sync?: string | null;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dups, src] = await Promise.all([
        apiClient.listDGCPPossibleDuplicates(partyType),
        apiClient.getDGCPSourceHealth(),
      ]);
      setItems((dups.items || []) as DupItem[]);
      setConservation(dups.conservation || null);
      setHealth(src);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando calidad de datos");
    } finally {
      setLoading(false);
    }
  }, [partyType]);

  useEffect(() => {
    void load();
  }, [load]);

  const act = async (item: DupItem, action: "merge" | "keep_separate" | "ignore") => {
    const a = item.supplier_a?.identity_key || item.institution_a?.identity_key;
    const b = item.supplier_b?.identity_key || item.institution_b?.identity_key;
    if (!a || !b) return;
    setActing(`${a}:${action}`);
    try {
      await apiClient.applyDGCPIdentityAction({
        party_type: partyType,
        identity_a: a,
        identity_b: b,
        action,
        criterion: item.reason,
        confidence: String(item.confidence),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Acción fallida");
    } finally {
      setActing(null);
    }
  };

  const healthDot =
    health?.status === "AVAILABLE" ? "🟢" : health?.status === "DEGRADED" ? "🟡" : "🔴";

  return (
    <div className="space-y-4 p-4 md:p-6">
      <AdminPageHeader
        title="Calidad de datos — Histórico DGCP"
        description="Posibles duplicados y estado de fuente. Solo administración."
      />

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span>
          DGCP API: {healthDot} {health?.status || "—"}
          {health?.http_status != null ? ` (HTTP ${health.http_status})` : ""}
        </span>
        {health?.last_successful_sync && (
          <span className="text-slate-500">Último sync OK: {health.last_successful_sync}</span>
        )}
        <Link href="/configuracion/integraciones/dgcp" className="text-sky-700 hover:underline">
          Integración DGCP
        </Link>
      </div>

      <div className="flex gap-2">
        <Button size="sm" variant={partyType === "supplier" ? "default" : "outline"} onClick={() => setPartyType("supplier")}>
          Proveedores
        </Button>
        <Button
          size="sm"
          variant={partyType === "institution" ? "default" : "outline"}
          onClick={() => setPartyType("institution")}
        >
          Instituciones
        </Button>
        <Button size="sm" variant="outline" onClick={() => void load()}>
          Refrescar
        </Button>
      </div>

      {conservation && (
        <p className="text-xs text-slate-500">
          Conservación índice: {conservation.lines} líneas · monto {conservation.total_amount} ·{" "}
          {conservation.processes} procesos · {conservation.supplier_rpe_identities} RPE ·{" "}
          {conservation.institution_code_identities} códigos institución
        </p>
      )}

      {error && <p className="text-sm text-amber-800">{error}</p>}
      {loading && (
        <p className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando…
        </p>
      )}

      <div className="space-y-3">
        {!loading && items.length === 0 && (
          <p className="text-sm text-slate-600">No hay candidatos de duplicado con las reglas actuales.</p>
        )}
        {items.map((item, idx) => {
          const a = item.supplier_a || item.institution_a;
          const b = item.supplier_b || item.institution_b;
          if (!a || !b) return null;
          return (
            <div key={`${a.identity_key}-${b.identity_key}-${idx}`} className="rounded border p-3">
              <div className="grid gap-2 text-sm md:grid-cols-2">
                <div>
                  <div className="font-medium">{a.display_name}</div>
                  <div className="text-xs text-slate-500">
                    {a.identity_key} · RPE/code {(item.rpe_a || (a as { code?: string }).code) || "—"} · adj{" "}
                    {a.awards_count}
                  </div>
                </div>
                <div>
                  <div className="font-medium">{b.display_name}</div>
                  <div className="text-xs text-slate-500">
                    {b.identity_key} · RPE/code {(item.rpe_b || (b as { code?: string }).code) || "—"} · adj{" "}
                    {b.awards_count}
                  </div>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                <span>{item.status}</span>
                <span>·</span>
                <span>confianza {item.confidence}</span>
                <span>·</span>
                <span>{item.reason}</span>
                {item.name_norm_a && (
                  <span className="w-full text-slate-400">
                    norm: {item.name_norm_a} ↔ {item.name_norm_b}
                  </span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  disabled={!!acting}
                  title="Unificación lógica reversible (no borra histórico)"
                  onClick={() => void act(item, "merge")}
                >
                  Unificar
                </Button>
                <Button size="sm" variant="outline" disabled={!!acting} onClick={() => void act(item, "keep_separate")}>
                  Mantener separados
                </Button>
                <Button size="sm" variant="ghost" disabled={!!acting} onClick={() => void act(item, "ignore")}>
                  Ignorar sugerencia
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
