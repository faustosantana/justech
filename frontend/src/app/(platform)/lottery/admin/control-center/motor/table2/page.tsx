"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { MotorNumberDetail, MotorNumberTable } from "@/components/lottery/control-center/motor-table";
import type { MotorTableRow } from "@/components/lottery/control-center/motor-types";
import { ApiError, apiClient } from "@/lib/api";

export default function Table2Page() {
  const params = useSearchParams();
  const [rows, setRows] = useState<MotorTableRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<MotorTableRow | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tables = await apiClient.getLotteryNumericRelationsTables();
      const list = (tables.table2 || []) as MotorTableRow[];
      setRows(list);
      const n = Number(params.get("n"));
      if (Number.isInteger(n) && n >= 1 && n <= 100) {
        setDetail(list.find((r) => r.number === n) || null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar Tabla 2");
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    void load();
  }, [load]);

  const onExport = async (format: "json" | "csv") => {
    try {
      const res = await apiClient.getLotteryNumericRelationsExport("table2", format);
      if (format === "csv" && typeof res.csv === "string") {
        await navigator.clipboard.writeText(res.csv);
        return;
      }
      await navigator.clipboard.writeText(JSON.stringify(res, null, 2));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export falló");
    }
  };

  const onDetail = async (row: MotorTableRow) => {
    try {
      const full = await apiClient.getLotteryNumericRelationsNumber(row.number, "table2");
      setDetail({ ...row, ...(full as MotorTableRow) });
    } catch {
      setDetail(row);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Motor Matemático · Tabla 2</h1>
      <p className="text-sm text-muted-foreground">
        Operación 1220 ÷ N · cadena de 12 dígitos · vista separada de Tabla 1
      </p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {loading ? <p className="text-sm text-muted-foreground">Cargando…</p> : null}
      <MotorNumberDetail row={detail} onClose={() => setDetail(null)} />
      {!loading ? (
        <MotorNumberTable
          rows={rows}
          table="table2"
          title="Tabla 2 — 100 números"
          onDetail={(r) => void onDetail(r)}
          onExport={(f) => void onExport(f)}
        />
      ) : null}
    </div>
  );
}
