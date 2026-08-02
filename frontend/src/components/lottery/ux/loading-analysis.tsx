"use client";

export function LoadingAnalysis({ label = "Interpretando resultados…" }: { label?: string }) {
  return (
    <div
      className="space-y-4 rounded-2xl border border-border/60 bg-card/80 p-5"
      role="status"
      aria-live="polite"
      data-testid="loading-analysis"
    >
      <div className="flex items-center gap-3">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/40" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
        </span>
        <p className="text-sm font-medium text-foreground">{label}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-xl bg-muted/70" />
        ))}
      </div>
      <div className="space-y-2">
        <div className="h-3 w-4/5 animate-pulse rounded bg-muted/70" />
        <div className="h-3 w-3/5 animate-pulse rounded bg-muted/60" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-muted/50" />
      </div>
    </div>
  );
}
