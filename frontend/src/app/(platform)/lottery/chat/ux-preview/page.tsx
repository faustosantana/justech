"use client";

import { AnalysisResponse } from "@/components/lottery/ux/analysis-response";
import { AppShell } from "@/components/layout/app-shell";

const MOCK_ROWS = Array.from({ length: 48 }, (_, i) => ({
  Fecha: `${2024 + (i % 3)}-${String((i % 12) + 1).padStart(2, "0")}-${String((i % 27) + 1).padStart(2, "0")}`,
  Lotería: ["Leidsa", "Loteka", "La Primera", "Real", "LoteDom", "Anguila"][i % 6],
  "Posición 02": i % 2 === 0 ? "Primera posición" : "Segunda posición",
  "Posición 20": i % 2 === 0 ? "Segunda posición" : "Primera posición",
  Resultado: `${String((i * 3) % 100).padStart(2, "0")}-${String((i * 7) % 100).padStart(2, "0")}-${String((i * 11) % 100).padStart(2, "0")}`,
}));

/** Preview visual de Lottery IA UX 2.0 con datos mock (sin motor/SQL). */
export default function LotteryUxPreviewPage() {
  return (
    <AppShell title="Lottery IA UX Preview" description="Demo visual de presentación de resultados">
      <div className="mx-auto max-w-6xl pb-10">
        <AnalysisResponse
          content="Los números 02 y 20 han coincidido en 105 ocasiones. La coincidencia más reciente ocurrió el 31 de mayo de 2026."
          query="¿Cuántas veces coincidieron el 02 y el 20?"
          latencyMs={842}
          toolTrace={[
            { tool: "workspace_sql", status: "ok", duration_ms: 210 },
            { tool: "ai_synthesis", status: "ok", duration_ms: 520 },
          ]}
          activeContext={{
            numbers: ["02", "20"],
            analyzing: "Coincidencias 02 + 20",
            filters_label: "2024–2026 · 6 loterías",
            relation: "02→20",
          }}
          sessionContext={{
            conversation_v4: {
              prompt_runtime: { version: "runtime-ux", provider: "demo", model: "preview", hash: "abc123" },
              prompt_studio: { version: "studio-ux" },
              workspace: "investigation",
            },
          }}
          structured={{
            type: "investigation_workspace_table",
            data: {},
            asset: {
              title: "Coincidencias entre 02 y 20",
              columns: ["Fecha", "Lotería", "Posición 02", "Posición 20", "Resultado"],
              rows: MOCK_ROWS,
              row_count: 105,
              filters: { a: "02", b: "20", from: "2024-01-01", to: "2026-05-31" },
              workspace: "investigation",
            },
          }}
        />
      </div>
    </AppShell>
  );
}
