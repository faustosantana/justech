"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import type { MotorTableRow, TableKind } from "./motor-types";

type SortKey = "number" | "code";

type Props = {
  rows: MotorTableRow[];
  table: TableKind;
  title: string;
  onDetail: (row: MotorTableRow) => void;
  onExport?: (format: "json" | "csv") => void;
  /** Si true, muestra panel colapsado de cálculo técnico (admin). */
  allowTechnical?: boolean;
};

export function MotorNumberTable({
  rows,
  table,
  title,
  onDetail,
  onExport,
  allowTechnical = false,
}: Props) {
  const [qNumber, setQNumber] = useState("");
  const [qCode, setQCode] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("number");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const [showTech, setShowTech] = useState(false);
  const pageSize = 25;

  const companionLabel = table === "table1" ? "Compañeros" : "Confirmadores relacionados";
  const companionCountLabel = table === "table1" ? "Cantidad de compañeros" : "Cantidad de confirmadores";

  const filtered = useMemo(() => {
    let list = [...rows];
    const n = qNumber.trim();
    const c = qCode.trim();
    if (n) list = list.filter((r) => String(r.number).includes(n));
    if (c) list = list.filter((r) => String(r.code ?? "").includes(c));
    list.sort((a, b) => {
      const av = Number(a[sortKey] ?? 0);
      const bv = Number(b[sortKey] ?? 0);
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return list;
  }, [rows, qNumber, qCode, sortKey, sortDir]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageRows = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

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
              <Button type="button" variant="ghost" size="sm" onClick={() => setShowTech((v) => !v)}>
                {showTech ? "Ocultar cálculo técnico" : "Ver cálculo técnico"}
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
            onChange={(e) => {
              setQNumber(e.target.value);
              setPage(0);
            }}
            className="max-w-[160px]"
          />
          <Input
            placeholder="Buscar código"
            value={qCode}
            onChange={(e) => {
              setQCode(e.target.value);
              setPage(0);
            }}
            className="max-w-[160px]"
          />
          <span className="self-center text-xs text-muted-foreground">
            {filtered.length} filas · pág. {page + 1}/{pageCount}
          </span>
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="cursor-pointer py-2 pr-3" onClick={() => toggleSort("number")}>
                Número
              </th>
              <th className="cursor-pointer py-2 pr-3" onClick={() => toggleSort("code")}>
                Código
              </th>
              <th className="py-2 pr-3">{companionLabel}</th>
              <th className="py-2 pr-3">{companionCountLabel}</th>
              <th className="py-2">Acción</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r) => {
              const companions = r.group_numbers || [];
              return (
                <tr key={`${table}-${r.number}`} className="border-b border-border/40 align-top">
                  <td className="py-1.5 pr-3 font-medium tabular-nums text-lg">{r.number}</td>
                  <td className="py-1.5 pr-3 font-semibold tabular-nums">{r.code}</td>
                  <td className="py-1.5 pr-3 text-xs text-muted-foreground">
                    {companions.join(", ") || "—"}
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">{companions.length}</td>
                  <td className="py-1.5">
                    <div className="flex flex-col gap-1 sm:flex-row">
                      <Button type="button" size="sm" className="min-h-11" onClick={() => onDetail(r)}>
                        Analizar
                      </Button>
                      <Button type="button" size="sm" variant="outline" className="min-h-11" asChild>
                        <Link
                          href={`/lottery/admin/control-center/motor/historial-numero?number=${r.number}&auto=1&featured=1`}
                        >
                          Ver expediente
                        </Link>
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {showTech && allowTechnical ? (
          <div className="mt-4 rounded border p-3 text-xs">
            <p className="mb-2 font-medium">Cálculo técnico (no forma parte de la vista principal)</p>
            <ul className="space-y-1 font-mono">
              {pageRows.slice(0, 5).map((r) => (
                <li key={`tech-${r.number}`}>
                  {r.number}: {r.formula} → {r.visible_value} · dígitos={r.digits_without_point} ·
                  cant={r.digit_count}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="mt-3 flex gap-2">
          <Button type="button" size="sm" variant="outline" disabled={page <= 0} onClick={() => setPage((p) => p - 1)}>
            Anterior
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={page >= pageCount - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Siguiente
          </Button>
        </div>
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
          <CardTitle className="text-base">Número {row.number}</CardTitle>
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
          <span className="font-medium">Código:</span> {row.code}
        </div>
        <div>
          <span className="font-medium">{table === "table1" ? "Compañeros:" : "Confirmadores:"}</span>{" "}
          {companions.join(", ") || "—"}
        </div>
        <div>
          <span className="font-medium">Cantidad:</span> {companions.length}
        </div>
        <details className="rounded border p-2 text-xs">
          <summary className="cursor-pointer font-medium">Ver cálculo técnico</summary>
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
