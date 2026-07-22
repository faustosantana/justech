"use client";

import Link from "next/link";

import type { ExecutiveActivityItem } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

function relativeTime(iso?: string | null): string {
  if (!iso) return "Reciente";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Ahora";
  if (mins < 60) return `Hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `Hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return `Hace ${days} d`;
}

type Props = {
  items: ExecutiveActivityItem[];
  className?: string;
};

export function HomeActivity({ items, className }: Props) {
  return (
    <section className={cn("home-glass rounded-2xl p-5 md:p-6", className)}>
      <h2 className="mb-4 text-sm font-semibold tracking-tight text-foreground">Actividad reciente</h2>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin actividad reciente.</p>
      ) : (
        <ul className="space-y-0">
          {items.map((item, i) => {
            const row = (
              <div className="flex gap-4 py-3">
                <div className="relative flex w-14 shrink-0 flex-col items-center">
                  <span className="text-[11px] font-medium text-muted-foreground">{relativeTime(item.timestamp)}</span>
                  {i < items.length - 1 && (
                    <span className="absolute top-8 h-[calc(100%-8px)] w-px bg-border/60" aria-hidden />
                  )}
                </div>
                <div className="min-w-0 flex-1 border-b border-border/30 pb-3 last:border-0">
                  <p className="text-sm font-medium text-foreground">{item.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{item.subtitle}</p>
                </div>
              </div>
            );
            return (
              <li key={item.id}>
                {item.href ? (
                  <Link href={item.href} className="block transition hover:bg-primary/5 rounded-lg -mx-2 px-2">
                    {row}
                  </Link>
                ) : (
                  row
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
