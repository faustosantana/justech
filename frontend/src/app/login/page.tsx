"use client";

import { Suspense, useEffect, useState } from "react";
import { ArrowRight, Building2, Lock, Mail, UserCircle2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

import { AuthField } from "@/components/auth/auth-field";
import { AuthLoadingState, AuthShell } from "@/components/auth/auth-shell";
import { CompanySelector } from "@/components/layout/company-selector";
import { CompanyContextProvider } from "@/lib/company-context";
import { apiClient } from "@/lib/api";
import { setAuthTokens } from "@/lib/auth";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthLoadingState message="Preparando acceso…" />}>
      <LoginPageContent />
    </Suspense>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [error, setError] = useState("");
  const [sessionNotice, setSessionNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [pickCompany, setPickCompany] = useState(false);

  useEffect(() => {
    if (searchParams.get("session") === "expired") {
      setSessionNotice("Tu sesión expiró. Inicia sesión de nuevo para continuar.");
    }
  }, [searchParams]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const tokens = await apiClient.login({
        email,
        password,
        tenant_slug: tenantSlug || undefined,
      });
      setAuthTokens(tokens);
      const allowed = await apiClient.getAllowedCompanies();
      if (allowed.items.length > 1) {
        setPickCompany(true);
        return;
      }
      if (allowed.items.length === 1) {
        await apiClient.setCompanyContext({
          selection_mode: "single",
          active_company_id: allowed.items[0].id,
          selected_company_ids: [allowed.items[0].id],
        });
      }
      router.push("/dashboard");
    } catch {
      setError("Credenciales inválidas o tenant incorrecto.");
    } finally {
      setLoading(false);
    }
  }

  if (pickCompany) {
    return (
      <CompanyContextProvider>
        <AuthShell
          title="Elige tu empresa"
          subtitle="Trabajarás con el contexto de la empresa seleccionada. Puedes cambiarlo después desde la barra superior."
        >
          <div className="space-y-6">
            <div className="brand-surface-accent rounded-xl p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
                <Building2 className="h-4 w-4 text-primary" />
                Contexto multiempresa
              </div>
              <CompanySelector />
            </div>
            <button type="button" className="auth-submit flex items-center justify-center gap-2" onClick={() => router.push("/dashboard")}>
              Continuar al panel
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </AuthShell>
      </CompanyContextProvider>
    );
  }

  return (
    <AuthShell
      title="Bienvenido de nuevo"
      subtitle="Accede a JAIOS con tu cuenta corporativa Justech. Usa el correo y tenant asignados por administración."
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <AuthField
          label="Correo corporativo"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="nombre@justech.do"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          icon={<Mail className="h-4 w-4" />}
          error={Boolean(error)}
          required
        />

        <AuthField
          label="Contraseña"
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          icon={<Lock className="h-4 w-4" />}
          error={Boolean(error)}
          required
        />

        <AuthField
          label="Organización (tenant)"
          name="tenant"
          placeholder="justech"
          value={tenantSlug}
          onChange={(e) => setTenantSlug(e.target.value)}
          icon={<UserCircle2 className="h-4 w-4" />}
          hint="Opcional si tu correo ya está asociado a un tenant."
        />

        {sessionNotice && (
          <p
            className={cn(
              "rounded-xl border px-4 py-3 text-sm",
              "border-warning/30 bg-warning/10 text-amber-950",
            )}
            role="status"
          >
            {sessionNotice}
          </p>
        )}

        {error && (
          <p
            className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            role="alert"
          >
            {error}
          </p>
        )}

        <button type="submit" className="auth-submit" disabled={loading}>
          {loading ? "Verificando acceso…" : "Entrar a JAIOS"}
        </button>
      </form>
    </AuthShell>
  );
}
