"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, LogOut, Settings, Sparkles, User } from "lucide-react";

import { BrandLogo } from "@/components/brand/brand-logo";
import { CompanySelector } from "@/components/layout/company-selector";
import { GlobalSearchBar } from "@/components/search/global-search-bar";
import { Button } from "@/components/ui/button";
import { useAssistantContext } from "@/lib/assistant-context";
import { clearAuthTokens } from "@/lib/auth";
import { cn } from "@/lib/utils";

type PlatformHeaderProps = {
  className?: string;
  title?: string;
  subtitle?: string;
};

export function PlatformHeader({ className, title, subtitle }: PlatformHeaderProps) {
  const router = useRouter();
  const { openCopilot } = useAssistantContext();

  function logout() {
    clearAuthTokens();
    router.push("/login");
  }

  return (
    <header className={cn("platform-header", className)}>
      <div className="flex min-w-0 shrink-0 items-center gap-3">
        <BrandLogo size="sm" showSubtitle={false} href="/dashboard" className="hidden sm:inline-flex" />
        {title ? (
          <>
            <h1 className="sr-only">{title}</h1>
            <div className="hidden min-w-0 lg:block" aria-hidden="true">
              <p className="truncate text-sm font-semibold text-foreground">{title}</p>
              {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
            </div>
          </>
        ) : null}
      </div>

      <CompanySelector compact />

      <GlobalSearchBar className="hidden min-w-0 flex-1 md:block" />

      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <Button variant="ghost" size="icon" className="relative h-9 w-9" asChild>
          <Link href="/notifications" aria-label="Notificaciones">
            <Bell className="h-4 w-4" />
          </Link>
        </Button>

        <Button
          type="button"
          variant="default"
          size="sm"
          className="hidden gap-1.5 sm:inline-flex"
          onClick={() => openCopilot()}
        >
          <Sparkles className="h-4 w-4" />
          Assistant
        </Button>
        <Button
          type="button"
          variant="default"
          size="icon"
          className="h-9 w-9 sm:hidden"
          onClick={() => openCopilot()}
          aria-label="Abrir Assistant"
        >
          <Sparkles className="h-4 w-4" />
        </Button>

        <Button variant="ghost" size="icon" className="h-9 w-9" asChild>
          <Link href="/configuracion" aria-label="Configuración">
            <Settings className="h-4 w-4" />
          </Link>
        </Button>

        <Button variant="outline" size="sm" className="hidden gap-1.5 md:inline-flex" onClick={logout}>
          <User className="h-4 w-4" />
          Salir
        </Button>
        <Button variant="ghost" size="icon" className="h-9 w-9 md:hidden" onClick={logout} aria-label="Cerrar sesión">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
