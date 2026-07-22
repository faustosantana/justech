"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api";

type Format = "csv" | "xlsx" | "pdf";

interface Props {
  queryType: string;
  queryParameters: Record<string, unknown>;
  title?: string;
  printHref?: string;
  disabled?: boolean;
}

/** Acciones de exportación e impresión reutilizables. */
export function LotteryExportActions({
  queryType,
  queryParameters,
  title,
  printHref,
  disabled,
}: Props) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<Format | null>(null);

  const run = async (format: Format) => {
    setBusy(format);
    setMsg(null);
    try {
      const exp = await apiClient.createLotteryExport({
        query_type: queryType,
        query_parameters: queryParameters,
        format,
        title,
      });
      await apiClient.downloadLotteryExport(exp.export_id, exp.filename);
      setMsg(`Descargado: ${exp.filename}`);
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "No se pudo exportar (¿permiso lottery.export?)");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {(["csv", "xlsx", "pdf"] as Format[]).map((fmt) => (
          <Button
            key={fmt}
            type="button"
            variant="secondary"
            size="sm"
            disabled={disabled || busy !== null}
            onClick={() => void run(fmt)}
            aria-label={`Exportar ${fmt.toUpperCase()}`}
          >
            {busy === fmt ? "…" : `Exportar ${fmt.toUpperCase()}`}
          </Button>
        ))}
        {printHref && (
          <Button asChild variant="outline" size="sm">
            <Link href={printHref}>Imprimir</Link>
          </Button>
        )}
      </div>
      {msg && (
        <p className="text-xs text-muted-foreground" role="status">
          {msg}
        </p>
      )}
    </div>
  );
}
