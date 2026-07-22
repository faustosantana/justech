"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ApiError, apiClient } from "@/lib/api";
import { DISCLAIMER, type DateQueryResponse } from "@/lib/lottery";

/** Vista print-friendly — sin shell/navegación. */
export default function LotteryPrintPage() {
  const params = useSearchParams();
  const lottery = params.get("lottery") || "Real";
  const date = params.get("date") || "2022-03-15";
  const [data, setData] = useState<DateQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setData(await apiClient.getLotteryByDate({ lottery, date }));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Error");
      }
    })();
  }, [lottery, date]);

  useEffect(() => {
    if (data) {
      const t = setTimeout(() => window.print(), 400);
      return () => clearTimeout(t);
    }
  }, [data]);

  return (
    <main className="mx-auto max-w-3xl p-8 print:p-4">
      <h1 className="text-2xl font-semibold">Resultados de Loterías</h1>
      <p className="text-sm text-muted-foreground">
        {lottery} · {date}
      </p>
      {error && <p className="text-destructive">{error}</p>}
      {data && (
        <div className="mt-6 space-y-4">
          <p>Lotería: {data.meta.resolved_lottery?.name || lottery}</p>
          <p>Sorteos: {data.total}</p>
          {data.draws.map((d) => (
            <div key={d.id} className="border-b py-3">
              <p className="text-sm">
                {d.draw_date}
                {d.source_reference ? ` · ref ${d.source_reference}` : ""}
              </p>
              <p className="font-mono text-3xl tracking-widest">
                {d.numbers.map((n) => n.number_raw || n.number_value).join("  ")}
              </p>
            </div>
          ))}
        </div>
      )}
      <p className="mt-8 text-xs">{DISCLAIMER}</p>
      <style jsx global>{`
        @media print {
          nav,
          aside,
          header,
          button,
          a {
            display: none !important;
          }
        }
      `}</style>
    </main>
  );
}
