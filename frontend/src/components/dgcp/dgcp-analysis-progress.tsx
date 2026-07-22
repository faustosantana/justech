"use client";

import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";

import type { DGCPAnalysisJob, DGCPAnalysisJobStage } from "@/lib/dgcp";
import { cn } from "@/lib/utils";

const STAGES: { key: DGCPAnalysisJobStage; label: string }[] = [
  { key: "preparing", label: "Preparando" },
  { key: "reading_documents", label: "Leyendo documentos" },
  { key: "hermes", label: "Hermes" },
  { key: "checklist", label: "Checklist" },
  { key: "expediente", label: "Expediente" },
  { key: "completed", label: "Completado" },
];

type Props = {
  job: DGCPAnalysisJob;
  className?: string;
};

export function DgcpAnalysisProgressPanel({ job, className }: Props) {
  const stageIndex = STAGES.findIndex((s) => s.key === job.stage);
  const isError = job.status === "error";
  const isDone = job.status === "completed";
  const stageLabel = STAGES.find((s) => s.key === job.stage)?.label ?? job.stage_label ?? job.stage;
  const detail =
    (job.error && job.error.trim().toLowerCase() !== "error" ? job.error : null) ??
    (job.message && job.message.trim().toLowerCase() !== "error" ? job.message : null);
  const title = isError
    ? "Análisis interrumpido"
    : isDone
      ? "Análisis completado"
      : `${stageLabel} en curso`;

  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3 space-y-3 text-sm",
        isError
          ? "border-destructive/40 bg-destructive/5"
          : isDone
            ? "border-success/40 bg-success/5"
            : "border-primary/30 bg-primary/5",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {isError ? (
          <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
        ) : isDone ? (
          <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
        ) : (
          <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />
        )}
        <div>
          <p className="font-medium">{title}</p>
          <p className="text-xs text-muted-foreground">
            {detail ??
              (isError
                ? "Revise el mensaje inferior o pulse «Analizar requisitos» para reintentar."
                : "Puede salir de esta pantalla; el resultado se guardará al terminar.")}
          </p>
        </div>
      </div>

      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-500",
            isError ? "bg-destructive" : isDone ? "bg-success" : "bg-primary",
          )}
          style={{ width: `${Math.min(100, Math.max(0, job.progress_pct))}%` }}
        />
      </div>

      <ol className="grid gap-1 sm:grid-cols-3 lg:grid-cols-6 text-[10px]">
        {STAGES.map((stage, idx) => {
          const active = job.stage === stage.key;
          const done = stageIndex > idx || isDone;
          return (
            <li
              key={stage.key}
              className={cn(
                "rounded px-2 py-1 text-center border",
                active && !isError && "border-primary bg-primary/10 text-primary font-medium",
                done && !active && "border-success/30 text-success",
                isError && active && "border-destructive/40 text-destructive",
                !done && !active && "border-transparent text-muted-foreground",
              )}
            >
              {stage.label}
            </li>
          );
        })}
      </ol>

      {isError && job.error ? (
        <p className="text-xs text-destructive">{job.error}</p>
      ) : null}
    </div>
  );
}
