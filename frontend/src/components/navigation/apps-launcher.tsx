"use client";

import Link from "next/link";
import { Star } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { FavoriteToggle } from "@/components/navigation/application-sidebar";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import { JAIOS_APPS, type JaiosApp } from "@/lib/app-registry";
import {
  filterAppsByAccess,
  getFavoriteAppIds,
  setCurrentAppId,
  toggleFavoriteApp,
} from "@/lib/app-navigation";
import { cn } from "@/lib/utils";

export function AppsLauncher() {
  const [favorites, setFavorites] = useState<string[]>(() => getFavoriteAppIds());
  const { access, loading } = usePlatformAccess();

  const apps = useMemo(
    () => filterAppsByAccess(
      JAIOS_APPS.filter((a) => !a.adminOnly),
      access,
    ),
    [access],
  );
  const favoriteApps = useMemo(() => apps.filter((a) => favorites.includes(a.id)), [apps, favorites]);
  const otherApps = useMemo(() => apps.filter((a) => !favorites.includes(a.id)), [apps, favorites]);

  const onToggleFavorite = useCallback((id: string) => {
    setFavorites(toggleFavoriteApp(id));
  }, []);

  return (
    <div className="mx-auto w-full max-w-5xl px-2 py-8 md:py-12">
      <header className="mb-10 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">JAIOS</h1>
        <p className="mt-2 text-sm text-muted-foreground">Selecciona una aplicación</p>
      </header>

      {loading ? (
        <p className="text-center text-sm text-muted-foreground">Cargando aplicaciones…</p>
      ) : apps.length === 0 ? (
        <p className="text-center text-sm text-muted-foreground">No hay aplicaciones disponibles para tu rol.</p>
      ) : (
        <>
          {favoriteApps.length > 0 && (
            <section className="mb-10">
              <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Favoritos</h2>
              <AppGrid apps={favoriteApps} favorites={favorites} onToggleFavorite={onToggleFavorite} />
            </section>
          )}

          <section>
            {favoriteApps.length > 0 && (
              <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Todas las aplicaciones</h2>
            )}
            <AppGrid apps={otherApps.length ? otherApps : apps} favorites={favorites} onToggleFavorite={onToggleFavorite} />
          </section>
        </>
      )}

      {access?.can_view_admin && (
        <div className="mt-10 flex justify-center">
          <Link
            href="/configuracion"
            className="text-sm text-muted-foreground transition hover:text-primary"
          >
            Configuración del sistema →
          </Link>
        </div>
      )}
    </div>
  );
}

function AppGrid({
  apps,
  favorites,
  onToggleFavorite,
}: {
  apps: JaiosApp[];
  favorites: string[];
  onToggleFavorite: (id: string) => void;
}) {
  return (
    <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4 sm:gap-4 md:grid-cols-5 lg:grid-cols-6">
      {apps.map((app) => {
        const Icon = app.icon;
        return (
          <li key={app.id} className="relative">
            <FavoriteToggle appId={app.id} favorited={favorites.includes(app.id)} onToggle={onToggleFavorite} />
            <Link
              href={app.homeHref}
              onClick={() => setCurrentAppId(app.id)}
              className="group flex flex-col items-center gap-2.5 rounded-2xl px-2 py-4 transition duration-300 hover:-translate-y-0.5 hover:bg-card/80 hover:shadow-lg"
            >
              <span
                className={cn(
                  "flex h-16 w-16 items-center justify-center rounded-2xl shadow-sm transition duration-300 group-hover:scale-105 group-hover:shadow-md sm:h-[4.5rem] sm:w-[4.5rem]",
                  app.accent,
                )}
              >
                <Icon className="h-7 w-7 sm:h-8 sm:w-8" strokeWidth={1.5} />
              </span>
              <span className="max-w-[6.5rem] text-center text-[11px] font-medium leading-tight text-foreground sm:text-xs">
                {app.label}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
