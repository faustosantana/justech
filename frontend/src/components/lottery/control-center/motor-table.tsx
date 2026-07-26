"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

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

  const filtered = useMemo(() => {
    let list = [...rows];
    const n = qNumber.trim();
    const c = qCode.trim();
    if (n) list = list.filter((r) => String(r.number).includes(n));
    if (c) list = list.filter((r) => String(r.code ?? "").includes(c));
    // Phase 5.2 UX: always sort by Código ascending; show all (up to 100) — no pagination
    list.sort((a, b) => Number(a.code ?? 0) - Number(b.code ?? 0));
    return list;
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
            {filtered.length} registros · ordenados por Código · sin paginación
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
            {filtered.map((r) => {
              const companions = r.group_numbers || [];
              return (
                <tr key={`${table}-${r.number}`} className="border-b border-border/40 align-top">
                  <td className="py-1.5 pr-3 font-semibold tabular-nums">{r.code}</td>
                  <td className="py-1.5 pr-3 text-xs text-muted-foreground">
                    {companions.join(", ") || "—"}
                  </td>
                  <td className="py-1.5">
                    <div className="flex flex-col gap-1 sm:flex-row">
                      <Button type="button" size="sm" className="min-h-11" asChild>
                        <Link href={analyzeHref(r.number)}>Analizar</Link>
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="min-h-11"
                        onClick={() => onDetail(r)}
                      >
                        Ver detalle
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {showTech && allowTechnical ? (
          <div className="mt-4 rounded border p-3 text-xs" role="region" aria-label="Cálculo técnico">
            <p className="mb-2 font-medium">Cálculo técnico (no forma parte de la vista principal)</p>
            <ul className="space-y-1 font-mono">
              {filtered.slice(0, 8).map((r) => (
                <li key={`tech-${r.number}`}>
                  {r.number}: {r.formula} → {r.visible_value} · dígitos={r.digits_without_point} ·
                  cant={r.digit_count}
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
  const companions = row.group_numbers || [];
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
