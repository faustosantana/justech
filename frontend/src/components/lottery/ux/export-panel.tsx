"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { AnalysisPresentation } from "@/lib/lottery-ux-present";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function toCsv(columns: string[], rows: Record<string, unknown>[]): string {
  const esc = (v: unknown) => {
    const s = String(v ?? "");
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const lines = [
    columns.map(esc).join(","),
    ...rows.map((r) => columns.map((c) => esc(r[c])).join(",")),
  ];
  return lines.join("\n");
}

/** Minimal SpreadsheetML so Excel opens it without a heavy XLSX lib. */
function toExcelXml(columns: string[], rows: Record<string, unknown>[]): string {
  const cell = (v: unknown) =>
    `<Cell><Data ss:Type="String">${String(v ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")}</Data></Cell>`;
  const header = `<Row>${columns.map(cell).join("")}</Row>`;
  const body = rows.map((r) => `<Row>${columns.map((c) => cell(r[c])).join("")}</Row>`).join("");
  return `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Resultados"><Table>${header}${body}</Table></Worksheet>
</Workbook>`;
}

export function ExportPanel({
  presentation,
  onStatus,
}: {
  presentation: AnalysisPresentation;
  onStatus?: (msg: string) => void;
}) {
  const [busy, setBusy] = useState<"csv" | "xlsx" | null>(null);
  const { columns, rows, downloadUrl, downloadFilename, title } = presentation;

  const exportCsv = () => {
    if (!columns.length || !rows.length) {
      onStatus?.("No hay filas para exportar");
      return;
    }
    setBusy("csv");
    try {
      const blob = new Blob([toCsv(columns, rows)], { type: "text/csv;charset=utf-8" });
      downloadBlob(blob, `${slug(title)}.csv`);
      onStatus?.("CSV descargado");
    } finally {
      setBusy(null);
    }
  };

  const exportXlsx = () => {
    if (downloadUrl) {
      window.open(downloadUrl, "_blank", "noopener,noreferrer");
      onStatus?.(`Descarga: ${downloadFilename || "export.xlsx"}`);
      return;
    }
    if (!columns.length || !rows.length) {
      onStatus?.("No hay filas para exportar");
      return;
    }
    setBusy("xlsx");
    try {
      const xml = toExcelXml(columns, rows);
      const blob = new Blob([xml], { type: "application/vnd.ms-excel" });
      downloadBlob(blob, `${slug(title)}.xls`);
      onStatus?.("Excel descargado");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-3 rounded-2xl border border-border/60 bg-card/80 p-4" data-testid="export-panel">
      <h3 className="text-sm font-semibold">Exportar</h3>
      <p className="text-sm text-muted-foreground">
        Descarga los {rows.length} registro(s) visibles de esta respuesta.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="secondary" disabled={busy !== null} onClick={exportCsv}>
          {busy === "csv" ? "…" : "Exportar CSV"}
        </Button>
        <Button type="button" size="sm" variant="secondary" disabled={busy !== null} onClick={exportXlsx}>
          {busy === "xlsx" ? "…" : "Exportar Excel"}
        </Button>
        {downloadUrl ? (
          <Button type="button" size="sm" variant="outline" asChild>
            <a href={downloadUrl} data-testid="workspace-excel-download">
              Descargar archivo del workspace
            </a>
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function slug(s: string) {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/gi, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 48) || "lottery-ia"
  );
}

export { toCsv, toExcelXml, downloadBlob };
