"use client";

import Link from "next/link";
import { Building2, ShieldCheck, Sparkles } from "lucide-react";

import { BrandLogo } from "@/components/brand/brand-logo";
import { CopyrightYear } from "@/components/brand/copyright-year";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/utils";

type AuthShellProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  className?: string;
};

const BRAND_POINTS = [
  {
    icon: Sparkles,
    title: "Inteligencia operativa",
    text: "Ventas, licitaciones, documentos y tareas en un solo centro de mando.",
  },
  {
    icon: Building2,
    title: "Multiempresa Just Group",
    text: "Contexto por empresa Odoo con visibilidad controlada por rol.",
  },
  {
    icon: ShieldCheck,
    title: "Seguro y auditable",
    text: "Acceso por tenant, trazabilidad y permisos granulares.",
  },
];

export function AuthShell({ title, subtitle, children, className }: AuthShellProps) {
  return (
    <div className="flex min-h-screen bg-background">
      <aside className="relative hidden w-[44%] max-w-xl overflow-hidden lg:flex lg:flex-col lg:justify-between">
        <div className="auth-brand-panel absolute inset-0" />
        <div className="auth-brand-grid absolute inset-0 opacity-40" />

        <div className="relative z-10 flex flex-col gap-10 p-10 xl:p-14">
          <div className="space-y-6">
            <BrandLogo size="lg" inverted href={BRAND.website} />
            <div className="space-y-3">
              <p className="brand-chip border-white/15 bg-white/10 text-blue-100">{BRAND.tagline}</p>
              <h1 className="text-3xl font-semibold leading-tight text-white xl:text-4xl">{BRAND.headline}</h1>
              <p className="max-w-md text-sm leading-relaxed text-blue-100/80">
                Plataforma empresarial de {BRAND.company} para operar ventas, DGCP, documentos y equipos con
                contexto multiempresa.
              </p>
            </div>
          </div>

          <ul className="space-y-4">
            {BRAND_POINTS.map(({ icon: Icon, title: pointTitle, text }) => (
              <li
                key={pointTitle}
                className="flex gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm transition hover:bg-white/10"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 text-blue-100">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{pointTitle}</p>
                  <p className="mt-1 text-xs leading-relaxed text-blue-100/75">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative z-10 border-t border-white/10 px-10 py-6 xl:px-14">
          <p className="text-xs text-blue-100/60">
            © <CopyrightYear />{" "}
            <Link href={BRAND.website} target="_blank" rel="noopener noreferrer" className="text-blue-100 hover:text-white">
              {BRAND.companyLegal}
            </Link>
            {" · "}Santo Domingo, Rep. Dom.
          </p>
        </div>
      </aside>

      <div className="platform-backdrop flex min-w-0 flex-1 flex-col">
        <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10 lg:px-16">
          <div className={cn("w-full max-w-[440px]", className)}>
            <div className="mb-8 lg:hidden">
              <BrandLogo size="md" href="/dashboard" />
            </div>

            <div className="auth-form-shell p-8 sm:p-10">
              <div className="mb-8 space-y-3">
                <span className="brand-chip">Acceso corporativo</span>
                <h2 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h2>
                <p className="text-sm leading-relaxed text-muted-foreground">{subtitle}</p>
              </div>
              {children}
            </div>

            <p className="mt-6 text-center text-xs text-muted-foreground lg:hidden">
              <Link href={BRAND.website} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                justech.do
              </Link>
              {" · "}
              {BRAND.tagline}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export { LoadingState as AuthLoadingState } from "@/components/brand/loading-state";
