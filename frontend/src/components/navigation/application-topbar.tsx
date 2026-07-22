"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, ChevronRight, LogOut, Search, Settings, Sparkles, User } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { CompanySelector } from "@/components/layout/company-selector";
import { buildBreadcrumbs, contextualSearchHref } from "@/lib/app-navigation";
import type { JaiosApp } from "@/lib/app-registry";
import { useAssistantContext } from "@/lib/assistant-context";
import { clearAuthTokens } from "@/lib/auth";
import { cn } from "@/lib/utils";

type Props = {
  app: JaiosApp | null;
  pathname: string;
  search: string;
  className?: string;
};

export function ApplicationTopbar({ app, pathname, search, className }: Props) {
  const router = useRouter();
  const { openCopilot } = useAssistantContext();
  const [query, setQuery] = useState("");
  const crumbs = buildBreadcrumbs(app, pathname, search);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        const el = document.getElementById("app-contextual-search") as HTMLInputElement | null;
        el?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function logout() {
    clearAuthTokens();
    router.push("/login");
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 2) return;
    router.push(contextualSearchHref(app, q));
  }

  return (
    <header className={cn("flex h-14 shrink-0 items-center gap-3 border-b border-border/80 bg-card/90 px-4 backdrop-blur-md md:gap-4 md:px-5", className)}>
      <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-1 text-sm md:flex">
        {crumbs.map((crumb, i) => (
          <span key={`${crumb.label}-${i}`} className="flex min-w-0 items-center gap-1">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground/60" />}
            {crumb.href ? (
              <Link href={crumb.href} className="truncate text-muted-foreground transition hover:text-foreground">
                {crumb.label}
              </Link>
            ) : (
              <span className="truncate font-medium text-foreground">{crumb.label}</span>
            )}
          </span>
        ))}
      </nav>

      <form onSubmit={handleSearch} className="flex min-w-0 flex-1 justify-center">
        <div className="relative w-full max-w-xl">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            id="app-contextual-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={app?.searchPlaceholder ?? "Buscar en JAIOS…"}
            className="h-9 w-full rounded-xl border border-border/60 bg-background/70 pl-9 pr-16 text-sm outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
          />
          <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-border/80 bg-muted/50 px-1.5 py-0.5 text-[10px] text-muted-foreground sm:inline">
            ⌘K
          </kbd>
        </div>
      </form>

      <CompanySelector compact />

      <div className="flex shrink-0 items-center gap-1">
        <Link href="/notifications" className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted" aria-label="Notificaciones">
          <Bell className="h-4 w-4" />
        </Link>
        <button type="button" onClick={() => openCopilot()} className="hidden h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground sm:inline-flex">
          <Sparkles className="h-4 w-4" />
          Assistant
        </button>
        <Link href="/configuracion" className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted" aria-label="Configuración">
          <Settings className="h-4 w-4" />
        </Link>
        <button type="button" onClick={logout} className="hidden h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm md:inline-flex">
          <User className="h-4 w-4" />
          Salir
        </button>
        <button type="button" onClick={logout} className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted md:hidden" aria-label="Salir">
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
