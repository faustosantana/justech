"use client";

import {
  CheckCircle2,
  ExternalLink,
  FileText,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type {
  DGCPComplianceMatrixRow,
  DGCPProductIntelligenceItem,
  DGCPProductIntelligenceResponse,
} from "@/lib/dgcp";
import { dgcpExpedienteTechnicalIntelligenceEnabled } from "@/lib/dgcp-feature-flags";
import { cn } from "@/lib/utils";

const COMPLIANCE_LABELS: Record<string, string> = {
  cumple: "Cumple",
  cumple_parcial: "Cumple parcial",
  no_cumple: "No cumple",
  requiere_revision: "Requiere revisión",
};

const SUB_TABS = [
  { id: "detectados", label: "Bienes requeridos" },
  { id: "candidatos", label: "Alternativas sugeridas" },
  { id: "matriz", label: "Matriz de cumplimiento" },
  { id: "fichas", label: "Fichas técnicas" },
  { id: "comercial", label: "Referencia comercial" },
] as const;

type SubTab = (typeof SUB_TABS)[number]["id"];

type Props = { opportunityId: string; embedded?: boolean };

export function DgcpExpedienteTechnicalIntelligencePanel({ opportunityId, embedded = false }: Props) {
  const enabled = dgcpExpedienteTechnicalIntelligenceEnabled();
  const [data, setData] = useState<DGCPProductIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subTab, setSubTab] = useState<SubTab>("detectados");
  const [selectedReqId, setSelectedReqId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPProductIntelligence(opportunityId);
      setData(res);
      if (!selectedReqId && res.items.length > 0) {
        setSelectedReqId(res.items[0].requirement.id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar la inteligencia técnica del expediente.");
    } finally {
      setLoading(false);
    }
  }, [enabled, opportunityId, selectedReqId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(
    () => data?.items.find((i) => i.requirement.id === selectedReqId) ?? data?.items[0] ?? null,
    [data, selectedReqId],
  );

  const selectedCandidate = useMemo(() => {
    if (!selected?.selected_candidate_id) return selected?.candidates[0] ?? null;
    return selected.candidates.find((c) => c.id === selected.selected_candidate_id) ?? null;
  }, [selected]);

  async function handleRun(force = false) {
    setRunning(true);
    setError(null);
    try {
      const res = await apiClient.runDGCPProductIntelligence(opportunityId, force);
      setData({
        opportunity_id: res.opportunity_id,
        enabled: true,
        summary: res.summary,
        items: res.items,
      });
      if (res.items.length > 0) setSelectedReqId(res.items[0].requirement.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al ejecutar pipeline.");
    } finally {
      setRunning(false);
    }
  }

  async function handleSearch(reqId: string) {
    setBusy(`search-${reqId}`);
    try {
      const res = await apiClient.searchDGCPProductCandidates(opportunityId, reqId);
      setData((prev) =>
        prev
          ? { ...prev, items: prev.items.map((i) => (i.requirement.id === reqId ? res.item : i)) }
          : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error en búsqueda.");
    } finally {
      setBusy(null);
    }
  }

  async function handleMatrix(reqId: string, candidateId: string) {
    setBusy(`matrix-${reqId}`);
    try {
      const res = await apiClient.buildDGCPComplianceMatrix(opportunityId, reqId, candidateId);
      setData((prev) =>
        prev
          ? { ...prev, items: prev.items.map((i) => (i.requirement.id === reqId ? res.item : i)) }
          : prev,
      );
      setSubTab("matriz");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al generar matriz.");
    } finally {
      setBusy(null);
    }
  }

  async function handleApprove(reqId: string, candidateId: string) {
    setBusy(`approve-${reqId}`);
    try {
      const res = await apiClient.approveDGCPProductIntelligence(opportunityId, reqId, candidateId);
      setData((prev) =>
        prev
          ? { ...prev, items: prev.items.map((i) => (i.requirement.id === reqId ? res.item : i)) }
          : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al aprobar producto.");
    } finally {
      setBusy(null);
    }
  }

  async function handleReject(reqId: string) {
    setBusy(`reject-${reqId}`);
    try {
      const res = await apiClient.rejectDGCPProductIntelligence(opportunityId, reqId);
      setData((prev) =>
        prev
          ? { ...prev, items: prev.items.map((i) => (i.requirement.id === reqId ? res.item : i)) }
          : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al rechazar.");
    } finally {
      setBusy(null);
    }
  }

  if (!enabled) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          Inteligencia técnica deshabilitada para este expediente (NEXT_PUBLIC_DGCP_PRODUCT_INTELLIGENCE=false).
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
        <Loader2 className="h-4 w-4 animate-spin" /> Cargando ingeniería de preventa…
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", embedded && "pt-1")}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Inteligencia técnica de la licitación
          </h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
            Parte del expediente: identifica bienes del pliego, alternativas compatibles, evidencia técnica
            y cumplimiento para la oferta. No es un catálogo ni inventario — responde qué cumple cada requisito.
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => void load()} disabled={running}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Actualizar
          </Button>
          <Button size="sm" onClick={() => void handleRun(false)} disabled={running}>
            {running ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Search className="h-3.5 w-3.5 mr-1" />}
            Analizar pliego técnico
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void handleRun(true)} disabled={running}>
            Reanalizar
          </Button>
        </div>
      </div>

      {error && (
        <p className="text-xs text-destructive border border-destructive/30 rounded p-2 bg-destructive/5">{error}</p>
      )}

      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <SummaryChip label="Bienes" value={data.summary.requirements_count} />
          <SummaryChip label="Alternativas" value={data.summary.candidates_count} />
          <SummaryChip label="Aprobados p/ oferta" value={data.summary.approved_count} />
          <SummaryChip
            label="Cumplimiento prom."
            value={data.summary.avg_compliance_pct != null ? `${data.summary.avg_compliance_pct}%` : "—"}
          />
          <SummaryChip label="Recomendado" value={data.summary.recommended_product ?? "—"} />
        </div>
      )}

      <div className="flex flex-wrap gap-1 border-b pb-2">
        {SUB_TABS.map((t) => (
          <Button
            key={t.id}
            size="sm"
            variant={subTab === t.id ? "default" : "ghost"}
            className="h-7 text-xs"
            onClick={() => setSubTab(t.id)}
          >
            {t.label}
          </Button>
        ))}
      </div>

      {!data?.items.length ? (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            Sin bienes técnicos detectados en el pliego. Ejecute <strong>Analizar pliego técnico</strong> tras el análisis de requisitos.
          </CardContent>
        </Card>
      ) : (
        <div className="grid lg:grid-cols-[240px_1fr] gap-4">
          <div className="space-y-1">
            {data.items.map((item) => (
              <button
                key={item.requirement.id}
                type="button"
                onClick={() => setSelectedReqId(item.requirement.id)}
                className={cn(
                  "w-full text-left rounded border px-2 py-2 text-xs transition-colors",
                  selectedReqId === item.requirement.id
                    ? "border-primary bg-primary/5"
                    : "border-transparent hover:bg-muted/50",
                )}
              >
                <div className="font-medium truncate">{item.requirement.nombre}</div>
                <div className="flex items-center gap-1 mt-1 flex-wrap">
                  <Badge variant="outline" className="text-[9px] h-4">
                    {item.requirement.categoria ?? "Equipo"}
                  </Badge>
                  {item.recommended && (
                    <Badge className="text-[9px] h-4">Recomendado</Badge>
                  )}
                  {item.compliance_pct != null && (
                    <span className="text-[9px] text-muted-foreground">{item.compliance_pct}%</span>
                  )}
                </div>
              </button>
            ))}
          </div>

          {selected && (
            <div className="space-y-4 min-w-0">
              {subTab === "detectados" && <DetectedSection item={selected} />}
              {subTab === "candidatos" && (
                <CandidatesSection
                  item={selected}
                  busy={busy}
                  onSearch={() => void handleSearch(selected.requirement.id)}
                  onMatrix={(cid) => void handleMatrix(selected.requirement.id, cid)}
                  onApprove={(cid) => void handleApprove(selected.requirement.id, cid)}
                  onReject={() => void handleReject(selected.requirement.id)}
                />
              )}
              {subTab === "matriz" && <MatrixSection item={selected} candidate={selectedCandidate} />}
              {subTab === "fichas" && <SheetsSection item={selected} opportunityId={opportunityId} />}
              {subTab === "comercial" && <CommercialSection item={selected} />}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SummaryChip({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border px-2 py-1.5">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="text-sm font-medium truncate">{value}</p>
    </div>
  );
}

function DetectedSection({ item }: { item: DGCPProductIntelligenceItem }) {
  const req = item.requirement;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{req.nombre}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        <div className="flex flex-wrap gap-2">
          {req.cantidad != null && (
            <Badge variant="secondary">Cantidad: {req.cantidad} {req.unidad ?? "u."}</Badge>
          )}
          <Badge variant="outline">Confianza: {Math.round((req.confidence ?? 0) * 100)}%</Badge>
          <Badge variant="outline">Estado: {item.status}</Badge>
        </div>
        {req.source_fragment && (
          <div className="rounded bg-muted/40 p-2 text-[11px]">
            <p className="font-medium mb-1">Evidencia pliego</p>
            <p className="text-muted-foreground whitespace-pre-wrap">{req.source_fragment}</p>
          </div>
        )}
        <div>
          <p className="font-medium mb-1">Requisitos técnicos</p>
          <ul className="list-disc pl-4 space-y-1">
            {req.technical_requirements.map((s, i) => (
              <li key={i}>
                {s.text}
                {s.page && <span className="text-muted-foreground"> (p. {s.page})</span>}
              </li>
            ))}
          </ul>
        </div>
        {req.functional_requirements.length > 0 && (
          <div>
            <p className="font-medium mb-1">Requisitos funcionales</p>
            <ul className="list-disc pl-4 space-y-1">
              {req.functional_requirements.map((s, i) => (
                <li key={i}>{s.text}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CandidatesSection({
  item,
  busy,
  onSearch,
  onMatrix,
  onApprove,
  onReject,
}: {
  item: DGCPProductIntelligenceItem;
  busy: string | null;
  onSearch: () => void;
  onMatrix: (candidateId: string) => void;
  onApprove: (candidateId: string) => void;
  onReject: () => void;
}) {
  const reqId = item.requirement.id;
  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm">Alternativas sugeridas para el requisito</CardTitle>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={onSearch} disabled={!!busy}>
            {busy === `search-${reqId}` ? <Loader2 className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}
            <span className="ml-1">Buscar</span>
          </Button>
          <Button size="sm" variant="destructive" className="h-7 text-[10px]" onClick={onReject} disabled={!!busy}>
            <ThumbsDown className="h-3 w-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {!item.candidates.length && (
          <p className="text-xs text-muted-foreground">Sin candidatos — ejecute búsqueda.</p>
        )}
        {item.candidates.map((c) => (
          <div key={c.id} className="rounded border p-2 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-xs font-medium">{c.name}</p>
                <p className="text-[10px] text-muted-foreground">
                  {c.manufacturer} · {c.model ?? c.sku ?? "—"} · {c.source}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {c.is_technical_source ? (
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" aria-label="Fuente técnica" />
                ) : (
                  <ShoppingCart className="h-3.5 w-3.5 text-amber-600" aria-label="Solo comercial" />
                )}
                <Badge variant="outline" className="text-[9px]">
                  {Math.round(c.confidence * 100)}%
                </Badge>
              </div>
            </div>
            {c.notes && <p className="text-[10px] text-muted-foreground">{c.notes}</p>}
            <div className="flex flex-wrap gap-1">
              {c.datasheet_url && (
                <Button size="sm" variant="ghost" className="h-6 text-[10px]" asChild>
                  <a href={c.datasheet_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-3 w-3 mr-1" /> Datasheet
                  </a>
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-[10px]"
                disabled={!!busy}
                onClick={() => onMatrix(c.id)}
              >
                Matriz
              </Button>
              <Button
                size="sm"
                className="h-6 text-[10px]"
                disabled={!!busy}
                onClick={() => onApprove(c.id)}
              >
                <ThumbsUp className="h-3 w-3 mr-1" /> Aprobar
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function MatrixSection({
  item,
  candidate,
}: {
  item: DGCPProductIntelligenceItem;
  candidate: DGCPProductIntelligenceItem["candidates"][0] | null;
}) {
  if (!item.compliance_matrix.length) {
    return (
      <Card>
        <CardContent className="py-6 text-xs text-muted-foreground text-center">
          Seleccione un candidato y genere la matriz de cumplimiento.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span>Matriz de cumplimiento</span>
          {item.compliance_pct != null && (
            <Badge>{item.compliance_pct}% cumplimiento</Badge>
          )}
        </CardTitle>
        {candidate && (
          <p className="text-[10px] text-muted-foreground">
            Producto: {candidate.name} · Fuente: {candidate.source_type}
          </p>
        )}
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-[10px] border-collapse">
          <thead>
            <tr className="border-b text-left">
              <th className="p-1">Requisito</th>
              <th className="p-1">Requerido</th>
              <th className="p-1">Producto</th>
              <th className="p-1">Estado</th>
              <th className="p-1">Evidencia</th>
            </tr>
          </thead>
          <tbody>
            {item.compliance_matrix.map((row, idx) => (
              <MatrixRow key={idx} row={row} />
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function MatrixRow({ row }: { row: DGCPComplianceMatrixRow }) {
  const ok = row.cumple === "cumple";
  const partial = row.cumple === "cumple_parcial";
  return (
    <tr className="border-b align-top">
      <td className="p-1">{row.requisito}</td>
      <td className="p-1 text-muted-foreground">{row.valor_requerido ?? "—"}</td>
      <td className="p-1">{row.valor_producto ?? "—"}</td>
      <td className="p-1">
        <span className="inline-flex items-center gap-0.5">
          {ok ? (
            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
          ) : partial ? (
            <ShieldCheck className="h-3 w-3 text-amber-600" />
          ) : (
            <XCircle className="h-3 w-3 text-muted-foreground" />
          )}
          {COMPLIANCE_LABELS[row.cumple] ?? row.cumple}
        </span>
      </td>
      <td className="p-1 text-muted-foreground">
        {row.fragmento && <p>{row.fragmento}</p>}
        {row.fuente && <p className="text-[9px]">Fuente: {row.fuente}{row.pagina ? ` · p. ${row.pagina}` : ""}</p>}
        {row.observacion && <p className="italic">{row.observacion}</p>}
      </td>
    </tr>
  );
}

function SheetsSection({
  item,
  opportunityId,
}: {
  item: DGCPProductIntelligenceItem;
  opportunityId: string;
}) {
  if (!item.technical_sheet_id) {
    return (
      <Card>
        <CardContent className="py-6 text-xs text-muted-foreground text-center">
          Aprobe un bien para la oferta con <strong>Regenerar ficha</strong> para vincular la ficha técnica del expediente.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardContent className="py-4 space-y-2 text-xs">
        <p className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Ficha técnica vinculada: <code className="text-[10px]">{item.technical_sheet_id}</code>
        </p>
        <Button size="sm" variant="outline" asChild>
          <Link href={`/dgcp/${opportunityId}?tab=fichas-tecnicas`}>
            Abrir Fichas Técnicas
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function CommercialSection({ item }: { item: DGCPProductIntelligenceItem }) {
  const c = item.commercial;
  if (!c) {
    return (
      <Card>
        <CardContent className="py-6 text-xs text-muted-foreground text-center">
          Sin datos comerciales — genere matriz con un candidato vinculado a Odoo.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <ShoppingCart className="h-4 w-4" />
          Referencia comercial (Odoo) — no evidencia de cumplimiento
        </CardTitle>
      </CardHeader>
      <CardContent className="grid sm:grid-cols-2 gap-3 text-xs">
        <CommercialField label="Producto" value={c.product_name} />
        <CommercialField label="Último precio" value={c.last_price != null ? `RD$${c.last_price.toLocaleString()}` : null} />
        <CommercialField label="Último costo" value={c.last_cost != null ? `RD$${c.last_cost.toLocaleString()}` : null} />
        <CommercialField label="Margen prom." value={c.avg_margin_pct != null ? `${c.avg_margin_pct}%` : null} />
        <CommercialField label="Unidades vendidas" value={c.units_sold?.toLocaleString()} />
        <CommercialField label="Proveedor" value={c.supplier} />
        <CommercialField label="Última venta" value={c.last_sale_date} />
        <p className="sm:col-span-2 text-[10px] text-amber-700 bg-amber-500/10 rounded p-2">{c.disclaimer}</p>
      </CardContent>
    </Card>
  );
}

function CommercialField({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="font-medium">{value ?? "—"}</p>
    </div>
  );
}
