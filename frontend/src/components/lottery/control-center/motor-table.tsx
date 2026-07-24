"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import type { MotorTableRow, TableKind } from "./motor-types";

type SortKey = "number" | "code" | "digit_count";

type Props = {
  rows: MotorTableRow[];
  table: TableKind;
  title: string;
  onDetail: (row: MotorTableRow) => void;
  onExport?: (format: "json" | "csv") => void;
};

export function MotorNumberTable({ rows, table, title, onDetail, onExport }: Props) {
  const [qNumber, setQNumber] = useState("");
  const [qCode, setQCode] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("number");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const filtered = useMemo(() => {
    let list = [...rows];
    const n = qNumber.trim();
    const c = qCode.trim();
    if (n) {
      list = list.filter((r) => String(r.number).includes(n));
    }
    if (c) {
      list = list.filter((r) => String(r.code ?? "").includes(c));
    }
    list.sort((a, b) => {
      const av = Number(a[sortKey] ?? 0);
      const bv = Number(b[sortKey] ?? 0);
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return list;
  }, [rows, qNumber, qCode, sortKey, sortDir]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageRows = filtered.slice(page * pageSize, page * pageSize + pageSize);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const copyRow = async (row: MotorTableRow) => {
    const text = [
      `Tabla ${table === "table1" ? "1" : "2"}`,
      `Número ${row.number}`,
      `Fórmula ${row.formula}`,
      `Resultado ${row.visible_value}`,
      `Dígitos ${row.digits_without_point}`,
      `Código ${row.code}`,
      `Grupo ${(row.group_numbers || []).join(", ")}`,
    ].join("\n");
    await navigator.clipboard.writeText(text);
  };

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <p className="text-sm text-muted-foreground">
              Universo fijo 1–100 · Solo lectura · No se mezcla con la otra tabla
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
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
              <th className="py-2 pr-3">Fórmula</th>
              <th className="py-2 pr-3">Resultado</th>
              <th className="py-2 pr-3">Cadena dígitos</th>
              <th className="cursor-pointer py-2 pr-3" onClick={() => toggleSort("digit_count")}>
                Cant. dígitos
              </th>
              <th className="cursor-pointer py-2 pr-3" onClick={() => toggleSort("code")}>
                Código
              </th>
              <th className="py-2 pr-3">Grupo</th>
              <th className="py-2">Acción</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r) => (
              <tr key={`${table}-${r.number}`} className="border-b border-border/40 align-top">
                <td className="py-1.5 pr-3 font-medium">{r.number}</td>
                <td className="py-1.5 pr-3 font-mono text-xs">{r.formula}</td>
                <td className="py-1.5 pr-3 font-mono text-xs">{r.visible_value}</td>
                <td className="py-1.5 pr-3 font-mono text-xs break-all">{r.digits_without_point}</td>
                <td className="py-1.5 pr-3">{r.digit_count}</td>
                <td className="py-1.5 pr-3 font-semibold">{r.code}</td>
                <td className="py-1.5 pr-3 text-xs">
                  <div className="font-medium">{r.group_label || `Código ${r.code}`}</div>
                  <div className="text-muted-foreground">{(r.group_numbers || []).join(", ")}</div>
                </td>
                <td className="py-1.5">
                  <div className="flex flex-col gap-1">
                    <Button type="button" size="sm" variant="outline" onClick={() => onDetail(r)}>
                      Ver detalle
                    </Button>
                    <Button type="button" size="sm" variant="ghost" onClick={() => void copyRow(r)}>
                      Copiar
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
}: {
  row: MotorTableRow | null;
  onClose: () => void;
}) {
  if (!row) return null;
  return (
    <Card className="border-primary/40">
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div>
          <CardTitle className="text-base">Detalle · Número {row.number}</CardTitle>
          <p className="text-xs text-muted-foreground">Solo lectura · calculado por el motor</p>
        </div>
        <Button type="button" size="sm" variant="ghost" onClick={onClose}>
          Cerrar
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div>
          <span className="font-medium">Operación:</span> <code>{row.formula}</code>
        </div>
        <div>
          <span className="font-medium">Valor decimal:</span> <code>{row.visible_value}</code>
        </div>
        <div>
          <span className="font-medium">Cadena exacta:</span>{" "}
          <code className="break-all">{row.digits_without_point}</code>
        </div>
        <div>
          <span className="font-medium">Suma literal:</span> {row.literal_digit_sum ?? row.code}
        </div>
        <div>
          <span className="font-medium">Código:</span> {row.code}
        </div>
        <div>
          <span className="font-medium">Integrantes del grupo:</span> {(row.group_numbers || []).join(", ")}
        </div>
        <div>
          <span className="font-medium">Implementación:</span>{" "}
          <code className="text-xs">{row.engine_ref || "NumericRelationsService"}</code>
        </div>
        <div className="rounded bg-muted px-2 py-1 text-xs">Indicador: solo lectura · editable=false</div>
      </CardContent>
    </Card>
  );
}
