"use client";

import Link from "next/link";
import { useMemo } from "react";

import { usePlatformAccess } from "@/hooks/use-platform-access";
import { LAUNCHER_APPS } from "@/lib/app-launcher";
import { filterLauncherApps } from "@/lib/app-navigation";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
};

export function AppLauncher({ className }: Props) {
  const { access, loading } = usePlatformAccess();
  const apps = useMemo(() => filterLauncherApps(LAUNCHER_APPS, access), [access]);

  return (
    <div className={cn("mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-6xl flex-col justify-center", className)}>
      <header className="mb-10 text-center md:mb-12">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
          Aplicaciones
        </h1>
        <p className="mt-2 text-sm text-muted-foreground md:text-base">
          Selecciona un módulo para comenzar
        </p>
      </header>

      {loading ? (
        <p className="text-center text-sm text-muted-foreground">Cargando aplicaciones…</p>
      ) : apps.length === 0 ? (
        <p className="text-center text-sm text-muted-foreground">No hay aplicaciones disponibles para tu rol.</p>
      ) : (
        <ul className="grid grid-cols-3 gap-4 sm:grid-cols-4 sm:gap-6 md:grid-cols-5 lg:grid-cols-6">
          {apps.map((app) => {
            const Icon = app.icon;
            return (
              <li key={app.id}>
                <Link
                  href={app.href}
                  className="group flex flex-col items-center gap-3 rounded-2xl px-2 py-4 text-center transition duration-200 hover:bg-card hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <span
                    className={cn(
                      "flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-2xl transition duration-200 group-hover:scale-105 group-hover:shadow-sm sm:h-20 sm:w-20",
                      app.accent,
                    )}
                  >
                    <Icon className="h-9 w-9 sm:h-10 sm:w-10" strokeWidth={1.5} aria-hidden />
                  </span>
                  <span className="max-w-[7.5rem] text-xs font-medium leading-snug text-foreground sm:text-sm">
                    {app.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
