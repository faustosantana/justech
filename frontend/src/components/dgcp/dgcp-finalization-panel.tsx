"use client";

import { Download, FileCheck, Loader2, Stamp } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { DGCPChecklist } from "@/lib/dgcp";
import type { DocumentFinalizationPreview, DocumentFinalizationRecord } from "@/lib/corporate-identity";

const FINALIZABLE_KEYS = new Set([
  "sncc_f033",
  "sncc_f034",
  "sncc_f042",
  "sncc_f047",
  "carta_presentacion",
  "oferta_economica",
  "oferta_tecnica",
]);

interface Props {
  opportunityId: string;
  checklist: DGCPChecklist | null;
  busy?: boolean;
  onUpdated: () => void;
}

export function DGCPFinalizationPanel({ opportunityId, checklist, busy, onUpdated }: Props) {
  const [preview, setPreview] = useState<DocumentFinalizationPreview | null>(null);
  const [records, setRecords] = useState<DocumentFinalizationRecord[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [panelBusy, setPanelBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const items = (checklist?.items ?? []).filter((i) => FINALIZABLE_KEYS.has(i.requirement_key ?? ""));

  const loadRecords = useCallback(async () => {
    try {
      const res = await apiClient.listDGCPFinalizationRecords(opportunityId);
      setRecords(res);
    } catch {
      setRecords([]);
    }
  }, [opportunityId]);

  useEffect(() => {
    void loadRecords();
  }, [loadRecords]);

  const runPreview = async (requirementKey: string, itemId?: string) => {
    setSelectedKey(requirementKey);
    setPanelBusy(true);
    setError(null);
    try {
      const p = await apiClient.previewDGCPFinalization(opportunityId, {
        requirement_key: requirementKey,
        checklist_item_id: itemId,
      });
      setPreview(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error en vista previa");
      setPreview(null);
    } finally {
      setPanelBusy(false);
    }
  };

  const generateOne = async () => {
    if (!selectedKey) return;
    setPanelBusy(true);
    setError(null);
    try {
      const item = items.find((i) => i.requirement_key === selectedKey);
      const res = await apiClient.generateDGCPFinalPdf(opportunityId, {
        requirement_key: selectedKey,
        checklist_item_id: item?.id,
      });
      setMessage(res.message);
      setPreview(null);
      await loadRecords();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al generar PDF final");
    } finally {
      setPanelBusy(false);
    }
  };

  const generateAll = async () => {
    setPanelBusy(true);
    setError(null);
    try {
      const res = await apiClient.generateAllDGCPFinalPdfs(opportunityId);
      setMessage(`${res.processed.length} PDF(s) final(es) generados`);
      if (res.warnings.length) setError(res.warnings.join(" · "));
      await loadRecords();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error en lote");
    } finally {
      setPanelBusy(false);
    }
  };

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Stamp className="h-4 w-4" />
          Firma, sello y PDF final
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Vista previa antes de generar — no modifica originales.{" "}
          <Link href="/documents/identity" className="text-primary hover:underline">
            Identidad corporativa
          </Link>
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void generateAll()} disabled={panelBusy || busy || items.length === 0}>
            {panelBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileCheck className="h-4 w-4 mr-2" />}
            Generar PDFs finales
          </Button>
        </div>

        {message && <p className="text-sm text-success">{message}</p>}
        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="border rounded divide-y max-h-48 overflow-y-auto">
          {items.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">Sin requisitos finalizables en checklist.</p>
          ) : (
            items.map((item) => (
              <div key={item.id} className="p-3 flex flex-wrap items-center justify-between gap-2 text-sm">
                <div>
                  <p className="font-medium">{item.requirement}</p>
                  <p className="text-xs text-muted-foreground">{item.status}</p>
                </div>
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={panelBusy}
                    onClick={() => void runPreview(item.requirement_key!, item.id)}
                  >
                    Vista previa
                  </Button>
                  <Button
                    size="sm"
                    disabled={panelBusy}
                    onClick={() => {
                      setSelectedKey(item.requirement_key!);
                      void runPreview(item.requirement_key!, item.id).then(() => generateOne());
                    }}
                  >
                    Generar PDF final
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>

        {preview && selectedKey && (
          <div className="rounded border bg-muted/20 p-3 space-y-2 text-sm">
            <p className="font-medium">Vista previa — {preview.document_title ?? selectedKey}</p>
            <p>
              Empresa: {preview.company_label} · Firma:{" "}
              {(preview.signature as { status?: string; filename?: string } | undefined)?.filename ?? "—"} (
              {(preview.signature as { status?: string } | undefined)?.status ?? "—"})
            </p>
            <p>
              Sello: {(preview.stamp as { filename?: string } | undefined)?.filename ?? "—"} (
              {(preview.stamp as { status?: string } | undefined)?.status ?? "—"})
            </p>
            {preview.warnings.length > 0 && (
              <ul className="text-warning text-xs">
                {preview.warnings.map((w) => (
                  <li key={w}>• {w}</li>
                ))}
              </ul>
            )}
            <Button size="sm" disabled={!preview.can_finalize || panelBusy} onClick={() => void generateOne()}>
              Generar PDF final
            </Button>
          </div>
        )}

        {records.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground mb-2">PDFs finales generados</p>
            <ul className="text-sm space-y-1">
              {records.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-2">
                  <span>
                    {r.output_filename} — {r.new_status}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void apiClient.downloadDGCPFinalPdf(opportunityId, r.id, r.output_filename)}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Descargar
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
