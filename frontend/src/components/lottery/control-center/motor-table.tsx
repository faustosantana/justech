"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { LotteryNumberLink } from "@/components/lottery/lottery-number-link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import type { MotorTableRow, TableKind } from "./motor-types";

type Props = {
  rows: MotorTableRow[];
  table: TableKind;
  title: string;
  onDetail: (row: MotorTableRow) => void;
  onExport?: (format: "json" | "csv") => void;
  allowTechnical?: boolean;
};

type GroupedRow = {
  code: number;
  companions: number[];
  /** Representative source row (for detail / analyze; number kept internally). */
  source: MotorTableRow;
  matchingNumbers: number[];
};

function groupByCode(rows: MotorTableRow[]): GroupedRow[] {
  const map = new Map<number, { companions: Set<number>; sources: MotorTableRow[]; numbers: number[] }>();
  for (const r of rows) {
    const code = Number(r.code ?? 0);
    let bucket = map.get(code);
    if (!bucket) {
      bucket = { companions: new Set<number>(), sources: [], numbers: [] };
      map.set(code, bucket);
    }
    bucket.sources.push(r);
    bucket.numbers.push(r.number);
    for (const n of r.group_numbers || []) {
      bucket.companions.add(Number(n));
    }
  }
  return [...map.entries()]
    .map(([code, bucket]) => {
      const companions = [...bucket.companions].sort((a, b) => a - b);
      // Prefer a source whose number is in the companion set; else first by number
      const sortedSources = [...bucket.sources].sort((a, b) => a.number - b.number);
      const source =
        sortedSources.find((s) => companions.includes(s.number)) || sortedSources[0];
      return {
        code,
        companions,
        source,
        matchingNumbers: [...bucket.numbers].sort((a, b) => a - b),
      };
    })
    .sort((a, b) => a.code - b.code);
}

export function MotorNumberTable({
  rows,
  table,
  title,
  onDetail,
  onExport,
  allowTechnical = true,
}: Props) {
  const [qNumber, setQNumber] = useState("");
  const [qCode, setQCode] = useState("");
  const [showTech, setShowTech] = useState(false);

  const companionLabel = table === "table1" ? "Compañeros" : "Confirmadores";
  const analyzeHref = (n: number) =>
    `/lottery/admin/control-center/motor/historial-numero?number=${n}&auto=1&featured=1`;

  const grouped = useMemo(() => {
    let list = [...rows];
    const n = qNumber.trim();
    const c = qCode.trim();
    if (n) {
      list = list.filter(
        (r) =>
          String(r.number).includes(n) ||
          (r.group_numbers || []).some((g) => String(g).includes(n)),
      );
    }
    if (c) list = list.filter((r) => String(r.code ?? "").includes(c));
    return groupByCode(list);
  }, [rows, qNumber, qCode]);

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {table === "table1"
                ? "Tabla 1 identifica los compañeros que se analizan cuando aparece un número."
                : "Tabla 2 identifica los números que pueden confirmar a un compañero de Tabla 1."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {allowTechnical ? (
              <Button
                type="button"
                variant={showTech ? "default" : "outline"}
                size="sm"
                onClick={() => setShowTech((v) => !v)}
              >
                {showTech ? "Ocultar cálculo" : "Ver cálculo"}
              </Button>
            ) : null}
            {onExport ? (
              <>
                <Button type="button" variant="outline" size="sm" onClick={() => onExport("json")}>
                  Export JSON
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={() => onExport("csv")}>
                  Export CSV
                </Button>
              </>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Buscar número"
            value={qNumber}
            onChange={(e) => setQNumber(e.target.value)}
            className="max-w-[160px]"
          />
          <Input
            placeholder="Buscar código"
            value={qCode}
            onChange={(e) => setQCode(e.target.value)}
            className="max-w-[160px]"
          />
          <span className="self-center text-xs text-muted-foreground">
            {grouped.length} códigos · agrupados · ordenados · sin paginación
          </span>
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 pr-3">Código</th>
              <th className="py-2 pr-3">{companionLabel}</th>
              <th className="py-2">Acción</th>
            </tr>
          </thead>
          <tbody>
            {grouped.map((g) => (
              <tr key={`${table}-code-${g.code}`} className="border-b border-border/40 align-top">
                <td className="py-1.5 pr-3 font-semibold tabular-nums">{g.code}</td>
                <td className="py-1.5 pr-3">
                  <div className="flex flex-wrap gap-1.5">
                    {g.companions.length
                      ? g.companions.map((n) => (
                          <LotteryNumberLink key={`${g.code}-${n}`} number={n} size="sm" />
                        ))
                      : "—"}
                  </div>
                </td>
                <td className="py-1.5">
                  <div className="flex flex-col gap-1 sm:flex-row">
                    <Button type="button" size="sm" className="min-h-11 bg-blue-600 hover:bg-blue-700" asChild>
                      <Link href={`/lottery/analizar?number=${g.source.number}&auto=1`}>Analizar</Link>
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="min-h-11"
                      onClick={() =>
                        onDetail({
                          ...g.source,
                          code: g.code,
                          group_numbers: g.companions,
                        })
                      }
                    >
                      Ver detalle
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {showTech && allowTechnical ? (
          <div className="mt-4 rounded border p-3 text-xs" role="region" aria-label="Cálculo técnico">
            <p className="mb-2 font-medium">Cálculo técnico (no forma parte de la vista principal)</p>
            <ul className="space-y-1 font-mono">
              {grouped.slice(0, 8).map((g) => (
                <li key={`tech-${g.code}`}>
                  código {g.code}: números={g.matchingNumbers.join(",")} · ref={g.source.number} ·{" "}
                  {g.source.formula} → {g.source.visible_value}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function MotorNumberDetail({
  row,
  onClose,
  table = "table1",
}: {
  row: MotorTableRow | null;
  onClose: () => void;
  table?: TableKind;
}) {
  if (!row) return null;
  const companions = [...(row.group_numbers || [])].sort((a, b) => a - b);
  return (
    <Card className="border-primary/40">
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div>
          <CardTitle className="text-base">Código {row.code}</CardTitle>
          <p className="text-xs text-muted-foreground">
            {table === "table1"
              ? "Compañeros identificados por Tabla 1"
              : "Confirmadores relacionados por Tabla 2"}
          </p>
        </div>
        <Button type="button" size="sm" variant="ghost" onClick={onClose}>
          Cerrar
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div>
          <span className="font-medium">Número de referencia:</span> {row.number}
        </div>
        <div>
          <span className="font-medium">Código:</span> {row.code}
        </div>
        <div>
          <span className="font-medium">{table === "table1" ? "Compañeros:" : "Confirmadores:"}</span>{" "}
          {companions.join(", ") || "—"}
        </div>
        <details className="rounded border p-2 text-xs">
          <summary className="cursor-pointer font-medium">Ver cálculo</summary>
          <div className="mt-2 space-y-1 font-mono">
            <div>Fórmula: {row.formula}</div>
            <div>Resultado: {row.visible_value}</div>
            <div className="break-all">Cadena: {row.digits_without_point}</div>
            <div>Cant. dígitos: {row.digit_count}</div>
          </div>
        </details>
      </CardContent>
    </Card>
  );
}
