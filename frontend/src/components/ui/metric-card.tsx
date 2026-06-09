import Link from "next/link";

import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  source?: string;
  href?: string;
  tone?: "primary" | "success" | "warning" | "danger" | "muted";
  delta?: string;
  actionLabel?: string;
}

const toneClasses = {
  primary: "border-primary/20 bg-primary/5",
  success: "border-success/20 bg-success/5",
  warning: "border-warning/30 bg-warning/5",
  danger: "border-destructive/20 bg-destructive/5",
  muted: "border-border bg-card",
};

export function MetricCard({
  label,
  value,
  source,
  href,
  tone = "primary",
  delta,
  actionLabel = "Ver detalle",
}: MetricCardProps) {
  const body = (
    <div className={cn("brand-surface rounded-xl p-4 transition hover:shadow-md", toneClasses[tone])}>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-bold tabular-nums tracking-tight">{value}</p>
      {delta && <p className="mt-1 text-xs text-muted-foreground">{delta}</p>}
      <div className="mt-3 flex items-center justify-between gap-2">
        {source && <span className="brand-chip normal-case tracking-normal text-muted-foreground">Fuente: {source}</span>}
        {href && <span className="text-xs font-medium text-primary">{actionLabel} →</span>}
      </div>
    </div>
  );

  if (href) {
    return <Link href={href}>{body}</Link>;
  }
  return body;
}
