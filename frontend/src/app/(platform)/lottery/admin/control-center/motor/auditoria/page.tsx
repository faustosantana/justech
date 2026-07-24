"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { MotorToolIntro } from "@/components/lottery/control-center/motor-tool-intro";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

const STATUS_LABELS = [
  "Cálculo verificado",
  "Histórico localizado",
  "Relación confirmada",
  "Sin confirmación",
  "Seguimiento incompleto",
];

type AuditRow = {
  draw_id: string;
  fecha_texto: string;
  loteria: string;
  lottery_id: string;
  estado: string;
  status: string;
  texto: string;
  candidatos_confirmados: number[];
  companions?: number[];
  confirmers?: number[];
  strengthened?: number | null;
  confirmation_count?: number;
  verification?: string;
  posterior?: string;
};

function verificationLabel(status: string, censored?: boolean): string {
  if (censored) return "Seguimiento incompleto";
  if (status === "yes" || status === "partial") return "Relación confirmada";
  if (status === "no") return "Sin confirmación";
  return "Histórico localizado";
}

export default function AuditoriaPage() {
  const [number, setNumber] = useState("50");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [lotteryId, setLotteryId] = useState("");
  const [drawId, setDrawId] = useState("");
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    void (async () => {
      try {
        const lots = await apiClient.getLotteryNumericRelationsLotteries();
        setCatalog((lots.items || []).filter((c) => c?.id));
      } catch {
        /* keep empty */
      }
    })();
  }, []);

  const featuredIds = useMemo(
    () => catalog.filter((c) => (c as LotOption & { is_featured?: boolean }).is_featured).map((c) => c.id),
    [catalog],
  );

  const scopeIds = useMemo(() => {
    if (lotteryId) return [lotteryId];
    if (featuredIds.length) return featuredIds;
    return catalog.map((c) => c.id).slice(0, 7);
  }, [lotteryId, featuredIds, catalog]);

  const expedienteHref = useMemo(() => {
    const params = new URLSearchParams({ auto: "1", featured: "1" });
    const n = Number(number);
    if (Number.isInteger(n) && n >= 1 && n <= 100) params.set("number", String(n));
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (lotteryId) params.set("lottery_ids", lotteryId);
    return `/lottery/admin/control-center/motor/historial-numero?${params.toString()}`;
  }, [number, dateFrom, dateTo, lotteryId]);

  const search = useCallback(async () => {
    setBusy(true);
    setError(null);
    setRows([]);
    try {
      const n = Number(number);
      if (!Number.isInteger(n) || n < 1 || n > 100) {
        throw new Error("El número debe estar entre 1 y 100");
      }
      if (!scopeIds.length) throw new Error("No hay loterías disponibles para auditar");

      const scope = {
        primary_lottery_ids: scopeIds,
        confirming_lottery_ids: scopeIds,
        follow_up_lottery_ids: scopeIds,
      };
      const confirmation_window = { mode: "SAME_DRAW", timezone: "America/Santo_Domingo" };
      const base = {
        number: n,
        scope,
        confirmation_window,
        max_horizon: 7,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      };

      if (drawId.trim()) {
        const detail = await apiClient.postLotteryNrNumberOccurrenceDetail({
          ...base,
          draw_id: drawId.trim(),
        });
        const tree = (detail.relation_tree || {}) as Record<string, unknown>;
        const branches = (tree.candidatos || []) as Record<string, unknown>[];
        const confirmed = branches.filter((b) => Number(b.confirmaciones) > 0);
        const strengthened = confirmed[0] ? Number(confirmed[0].candidato) : null;
        const confirmers = confirmed.flatMap(
          (b) => (b.confirmadores_encontrados || []) as number[],
        );
        const verdict = (detail.verdict || {}) as Record<string, unknown>;
        const st = String(verdict.status || detail.status || "");
        setTotal(1);
        setRows([
          {
            draw_id: drawId.trim(),
            fecha_texto: String((detail.anchor || detail).fecha_texto || detail.fecha_texto || "—"),
            loteria: String((detail.anchor || detail).loteria || detail.lottery_name || "—"),
            lottery_id: String((detail.anchor || detail).lottery_id || ""),
            estado: String(verdict.headline || "Cálculo verificado"),
            status: st,
            texto: String(detail.natural_line || ""),
            candidatos_confirmados: confirmed.map((b) => Number(b.candidato)),
            companions: (detail.table1_candidates as number[]) || branches.map((b) => Number(b.candidato)),
            confirmers: [...new Set(confirmers)],
            strengthened,
            confirmation_count: confirmers.length,
            verification: verificationLabel(st),
            posterior: "Ver expediente completo para los siete sorteos posteriores.",
          },
        ]);
        return;
      }

      const occ = await apiClient.postLotteryNrNumberOccurrences({
        ...base,
        page: 1,
        page_size: 8,
        condition: "all",
        order: "desc",
        lottery_id: lotteryId || undefined,
      });
      const items = ((occ.items || []) as Record<string, unknown>[]) || [];
      setTotal(Number(occ.total || items.length));

      const enriched: AuditRow[] = [];
      for (const item of items.slice(0, 5)) {
        const did = String(item.draw_id);
        let companions: number[] = [];
        let confirmers: number[] = [];
        let strengthened: number | null = null;
        let confirmation_count = 0;
        let posterior = "—";
        try {
          const detail = await apiClient.postLotteryNrNumberOccurrenceDetail({
            ...base,
            draw_id: did,
          });
          const tree = (detail.relation_tree || {}) as Record<string, unknown>;
          const branches = (tree.candidatos || []) as Record<string, unknown>[];
          companions = branches.map((b) => Number(b.candidato));
          const confirmed = branches.filter((b) => Number(b.confirmaciones) > 0);
          strengthened = confirmed[0] ? Number(confirmed[0].candidato) : null;
          confirmers = [
            ...new Set(
              confirmed.flatMap((b) => (b.confirmadores_encontrados || []) as number[]),
            ),
          ];
          confirmation_count = confirmers.length;
          posterior =
            confirmed.length > 0
              ? `Candidato fortalecido: ${strengthened}. Abrir expediente para seguimiento.`
              : "Sin confirmación en ventana; ver expediente para seguimiento.";
        } catch {
          companions = (item.candidatos_confirmados as number[]) || [];
        }
        const st = String(item.status || "");
        enriched.push({
          draw_id: did,
          fecha_texto: String(item.fecha_texto || item.fecha || "—"),
          loteria: String(item.loteria || "—"),
          lottery_id: String(item.lottery_id || ""),
          estado: String(item.estado || "—"),
          status: st,
          texto: String(item.texto || ""),
          candidatos_confirmados: (item.candidatos_confirmados as number[]) || [],
          companions,
          confirmers,
          strengthened,
          confirmation_count,
          verification: verificationLabel(st),
          posterior,
        });
      }
      setRows(enriched);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Búsqueda falló");
    } finally {
      setBusy(false);
    }
  }, [number, dateFrom, dateTo, lotteryId, drawId, scopeIds]);

  return (
    <div className="space-y-4">
      <MotorToolIntro
        title="Auditoría"
        description="Busque dentro de esta pantalla por número, fecha, lotería o draw_id. Verá compañeros, confirmadores, candidato fortalecido y estado de verificación sin depender solo del expediente."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Buscar casos auditables</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          <label className="text-sm">
            Número
            <Input className="mt-1" value={number} onChange={(e) => setNumber(e.target.value)} inputMode="numeric" />
          </label>
          <label className="text-sm">
            Desde
            <Input className="mt-1" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="text-sm">
            Hasta
            <Input className="mt-1" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
          <label className="text-sm md:col-span-2 lg:col-span-1">
            Lotería
            <select
              className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={lotteryId}
              onChange={(e) => setLotteryId(e.target.value)}
            >
              <option value="">7 destacadas</option>
              {catalog.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm md:col-span-2">
            Sorteo / draw_id
            <Input
              className="mt-1 font-mono text-xs"
              value={drawId}
              onChange={(e) => setDrawId(e.target.value)}
              placeholder="UUID opcional"
            />
          </label>
          <div className="flex items-end gap-2 md:col-span-3 lg:col-span-6">
            <Button type="button" className="min-h-11" disabled={busy} onClick={() => void search()}>
              {busy ? "Buscando…" : "Buscar en pantalla"}
            </Button>
            <Button asChild variant="outline" className="min-h-11">
              <Link href={expedienteHref}>Ver expediente completo</Link>
            </Button>
          </div>
          {error ? <p className="text-sm text-destructive md:col-span-6">{error}</p> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Estados visibles</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 text-sm">
          {STATUS_LABELS.map((s) => (
            <span key={s} className="rounded-full border px-3 py-1">
              {s}
            </span>
          ))}
          <span className="rounded-full border border-primary/40 px-3 py-1 text-primary">
            Cálculo verificado
          </span>
        </CardContent>
      </Card>

      {rows.length ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Resultados ({rows.length}
              {total > rows.length ? ` de ${total}` : ""})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {rows.map((r) => (
              <div key={r.draw_id} className="rounded-lg border p-3 text-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold">
                      Número {number} · {r.loteria} · {r.fecha_texto}
                    </div>
                    <div className="text-muted-foreground">{r.estado}</div>
                  </div>
                  <span className="rounded-full border px-2 py-0.5 text-xs">{r.verification}</span>
                </div>
                <p className="mt-2">{r.texto}</p>
                <dl className="mt-2 grid gap-1 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Compañeros (T1)</dt>
                    <dd>{(r.companions || []).join(", ") || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Confirmadores</dt>
                    <dd>{(r.confirmers || []).join(", ") || "ninguno"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Candidato fortalecido</dt>
                    <dd className="font-semibold">
                      {r.strengthened != null ? r.strengthened : "ninguno"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Confirmaciones</dt>
                    <dd>{r.confirmation_count ?? 0}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-xs uppercase text-muted-foreground">Resultado posterior</dt>
                    <dd>{r.posterior}</dd>
                  </div>
                </dl>
                <details className="mt-2 text-xs text-muted-foreground">
                  <summary className="cursor-pointer">Evidencia técnica</summary>
                  <p className="mt-1 font-mono break-all">draw_id={r.draw_id}</p>
                  <p>Cálculo verificado · Histórico localizado · JSON oculto por defecto.</p>
                </details>
                <div className="mt-2">
                  <Button asChild size="sm" variant="outline">
                    <Link
                      href={`/lottery/admin/control-center/motor/historial-numero?number=${number}&auto=1&featured=1`}
                    >
                      Ver expediente completo
                    </Link>
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cómo se verifica</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Cada caso ancla en un <strong>sorteo real</strong> (identidad = draw_id). El JSON técnico
            permanece oculto por defecto.
          </p>
          <p>
            La fuerza siempre pertenece al <strong>compañero de Tabla 1</strong>; el confirmador de
            Tabla 2 aporta evidencia, no se fortalece a sí mismo.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
