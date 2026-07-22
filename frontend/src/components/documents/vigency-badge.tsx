"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** Estados documentales: verde vigente, amarillo por vencer, rojo vencido/pendiente, gris opcional. */
export function vigencyTone(status: string | null | undefined, opts?: { required?: boolean; missing?: boolean }): "green" | "yellow" | "red" | "grey" {
  const s = (status || "").toLowerCase();
  if (opts?.missing || s === "falta" || s === "pendiente" || s === "missing") return "red";
  if (s.includes("vencido") || s === "expired" || s === "vencido") return "red";
  if (s.includes("proximo") || s.includes("próximo") || s === "proximo_a_vencer") return "yellow";
  if (s.includes("vigente") || s === "completo" || s === "documento cargado") return "green";
  if (!opts?.required && (s === "no_aplica" || s === "opcional" || s === "sin_fecha" || !s)) return "grey";
  if (opts?.required && !s) return "red";
  return "grey";
}

const TONE_CLASS: Record<string, string> = {
  green: "bg-emerald-500/15 text-emerald-800 border-emerald-500/40 dark:text-emerald-200",
  yellow: "bg-amber-500/15 text-amber-900 border-amber-500/40 dark:text-amber-200",
  red: "bg-red-500/15 text-red-800 border-red-500/40 dark:text-red-200",
  grey: "bg-muted text-muted-foreground border-border",
};

export function VigencyBadge({
  status,
  label,
  required,
  missing,
  className,
}: {
  status?: string | null;
  label?: string;
  required?: boolean;
  missing?: boolean;
  className?: string;
}) {
  const tone = vigencyTone(status, { required, missing });
  const text =
    label ||
    status ||
    (missing ? "Pendiente" : required === false ? "Opcional" : "Sin estado");

  return (
    <Badge variant="outline" className={cn(TONE_CLASS[tone], className)}>
      {text}
    </Badge>
  );
}
