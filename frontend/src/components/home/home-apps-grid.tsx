"use client";

import Link from "next/link";
import { useMemo } from "react";

import { LAUNCHER_APPS } from "@/lib/app-launcher";
import { filterLauncherApps } from "@/lib/app-navigation";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import { cn } from "@/lib/utils";

type Props = {
  compact?: boolean;
  className?: string;
};

export function HomeAppsGrid({ compact = false, className }: Props) {
  const { access, loading } = usePlatformAccess();
  const apps = useMemo(() => filterLauncherApps(LAUNCHER_APPS, access), [access]);

  return (
    <section className={cn(className)}>
      <h2 className="mb-4 text-sm font-semibold tracking-tight text-foreground">Mis aplicaciones</h2>
      {loading ? (
        <p className="text-sm text-muted-foreground">Cargando aplicaciones…</p>
      ) : apps.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay aplicaciones disponibles para tu rol.</p>
      ) : (
        <ul
          className={cn(
            "grid gap-2 sm:gap-3",
            compact
              ? "grid-cols-4 sm:grid-cols-6 md:grid-cols-8"
              : "grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8",
          )}
        >
          {apps.map((app) => {
            const Icon = app.icon;
            return (
              <li key={app.id}>
                <Link
                  href={app.href}
                  className="group flex flex-col items-center gap-2 rounded-2xl px-1 py-3 transition duration-300 hover:-translate-y-0.5 hover:bg-white/40 hover:shadow-lg dark:hover:bg-white/5"
                >
                  <span
                    className={cn(
                      "flex items-center justify-center rounded-2xl shadow-sm transition duration-300 group-hover:scale-105 group-hover:shadow-md",
                      compact ? "h-12 w-12" : "h-14 w-14 sm:h-16 sm:w-16",
                      app.accent,
                    )}
                  >
                    <Icon className={cn(compact ? "h-5 w-5" : "h-6 w-6 sm:h-7 sm:w-7")} strokeWidth={1.5} />
                  </span>
                  <span className="max-w-[5.5rem] text-center text-[10px] font-medium leading-tight text-foreground sm:text-[11px]">
                    {app.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
