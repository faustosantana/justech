import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import { BrandLogo } from "@/components/brand/brand-logo";
import { CopyrightYear } from "@/components/brand/copyright-year";
import { BRAND } from "@/lib/brand";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <aside className="relative hidden w-[44%] max-w-xl overflow-hidden lg:flex lg:flex-col lg:justify-between">
        <div className="auth-brand-panel absolute inset-0" />
        <div className="auth-brand-grid absolute inset-0 opacity-40" />
        <div className="relative z-10 flex flex-col gap-8 p-10 xl:p-14">
          <BrandLogo size="lg" inverted href={BRAND.website} />
          <div className="space-y-4">
            <p className="brand-chip border-white/15 bg-white/10 text-blue-100">{BRAND.tagline}</p>
            <h1 className="text-4xl font-semibold leading-tight text-white">{BRAND.headline}</h1>
            <p className="max-w-md text-sm leading-relaxed text-blue-100/80">
              {BRAND.product} es el centro de mando empresarial de {BRAND.company}: ventas, licitaciones,
              documentos, precios y equipos con inteligencia asistida.
            </p>
          </div>
        </div>
        <div className="relative z-10 border-t border-white/10 px-10 py-6 xl:px-14">
          <p className="text-xs text-blue-100/60">© <CopyrightYear /> {BRAND.companyLegal}</p>
        </div>
      </aside>

      <div className="platform-backdrop flex flex-1 flex-col items-center justify-center px-6 py-12 sm:px-10">
        <div className="w-full max-w-lg">
          <div className="mb-8 lg:hidden">
            <BrandLogo size="md" />
          </div>

          <div className="auth-form-shell p-8 sm:p-10">
            <div className="mb-8 space-y-3">
              <span className="brand-chip inline-flex items-center gap-1.5">
                <Sparkles className="h-3 w-3" />
                Plataforma empresarial
              </span>
              <h2 className="text-3xl font-bold tracking-tight">Opera tu negocio con {BRAND.product}</h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Autenticación multiempresa, asistente inteligente y módulos integrados para el grupo Justech.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Link href="/login" className="auth-submit inline-flex items-center justify-center gap-2">
                Iniciar sesión
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href={BRAND.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 items-center justify-center rounded-xl border border-border/80 bg-background px-6 text-sm font-medium text-foreground transition hover:border-primary/30 hover:bg-accent"
              >
                Conocer {BRAND.company}
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
