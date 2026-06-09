"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Link2, Shield, Unlink, User } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { OdooCompany, OdooMe } from "@/lib/odoo";
import { cn } from "@/lib/utils";

export default function OdooSettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<OdooMe | null>(null);
  const [companies, setCompanies] = useState<OdooCompany[]>([]);
  const [odooLogin, setOdooLogin] = useState("");
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [unlinking, setUnlinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setError(null);
    try {
      const [meRes, companiesRes] = await Promise.all([
        apiClient.getOdooMe(),
        apiClient.getOdooCompanies(),
      ]);
      setMe(meRes);
      setCompanies(companiesRes.items);
      if (meRes.user_mapping?.odoo_login) {
        setOdooLogin(meRes.user_mapping.odoo_login);
      }
    } catch {
      setError("No se pudo cargar la configuración Odoo.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  const handleLink = async () => {
    const login = odooLogin.trim();
    if (!login) {
      setError("Escribe el email o login de tu usuario Odoo.");
      return;
    }
    setLinking(true);
    setError(null);
    setSuccess(null);
    try {
      await apiClient.linkOdooUser(login);
      setSuccess("Usuario Odoo vinculado correctamente.");
      await load();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "ODOO_USER_NOT_FOUND") {
          setError("Usuario Odoo no encontrado.");
        } else if (err.code === "ODOO_NOT_CONNECTED") {
          setError("Odoo no conectado.");
        } else {
          setError(err.message);
        }
      } else {
        setError("No se pudo vincular el usuario Odoo.");
      }
    } finally {
      setLinking(false);
    }
  };

  const handleUnlink = async () => {
    setUnlinking(true);
    setError(null);
    setSuccess(null);
    try {
      await apiClient.unlinkOdooUser();
      setSuccess("Usuario Odoo desvinculado en JAIOS.");
      setOdooLogin("");
      await load();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No se pudo desvincular.");
      }
    } finally {
      setUnlinking(false);
    }
  };

  const mapping = me?.user_mapping;
  const linked = Boolean(mapping?.is_active && mapping.odoo_user_id);
  const allowedCompanies = companies.filter((c) =>
    mapping?.allowed_company_ids?.includes(c.id),
  );
  const defaultCompany = companies.find((c) => c.id === mapping?.default_company_id);

  return (
    <AppShell
      title="Configuración Odoo"
      description="Vincula tu usuario Odoo para filtrar compañías y contexto personal"
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" size="sm" asChild>
            <Link href="/odoo">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver a Odoo
            </Link>
          </Button>
          {me?.read_only && (
            <span className="flex items-center gap-1 rounded-full bg-success/10 px-3 py-1 text-xs font-medium text-success">
              <Shield className="h-3.5 w-3.5" />
              Solo lectura
            </span>
          )}
        </div>

        {loading && (
          <p className="text-sm text-muted-foreground">Cargando configuración…</p>
        )}

        {error && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">
            {error}
          </p>
        )}
        {success && (
          <p className="rounded-lg border border-success/30 bg-success/10 px-4 py-2 text-sm text-success">
            {success}
          </p>
        )}

        {!loading && me && !me.odoo_connected && (
          <Card className="border-amber-500/30 bg-warning/10">
            <CardContent className="py-4 text-sm text-amber-800">
              Odoo no conectado. Configura las credenciales admin en el backend.
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <User className="h-5 w-5" />
              Mi usuario Odoo
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="odoo-login" className="text-sm font-medium">
                Email / Login de Odoo
              </label>
              <input
                id="odoo-login"
                type="email"
                value={odooLogin}
                onChange={(e) => setOdooLogin(e.target.value)}
                placeholder="fausto@justech.do"
                disabled={!me?.odoo_connected || linking}
                className="w-full max-w-md rounded-lg border border-input bg-background px-3 py-2 text-sm"
              />
              <p className="text-xs text-muted-foreground">
                No se guarda contraseña ni API key. Solo se verifica el login en Odoo (lectura).
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                onClick={handleLink}
                disabled={!me?.odoo_connected || linking}
              >
                <Link2 className={cn("mr-2 h-4 w-4", linking && "animate-pulse")} />
                {linking ? "Verificando…" : "Verificar y vincular"}
              </Button>
              {linked && (
                <Button
                  variant="outline"
                  onClick={handleUnlink}
                  disabled={unlinking}
                >
                  <Unlink className="mr-2 h-4 w-4" />
                  {unlinking ? "Desvinculando…" : "Desvincular en JAIOS"}
                </Button>
              )}
            </div>

            {linked && mapping && (
              <div className="mt-4 space-y-3 rounded-lg border border-border bg-muted/30 p-4">
                <p className="flex items-center gap-2 text-sm font-medium text-success">
                  <CheckCircle2 className="h-4 w-4" />
                  Usuario Odoo vinculado
                </p>
                <dl className="grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-muted-foreground">Odoo user_id</dt>
                    <dd className="font-mono">{mapping.odoo_user_id}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Odoo partner_id</dt>
                    <dd className="font-mono">{mapping.odoo_partner_id ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Login Odoo</dt>
                    <dd>{mapping.odoo_login}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Compañía por defecto</dt>
                    <dd>
                      {defaultCompany
                        ? `${defaultCompany.name} (#${mapping.default_company_id})`
                        : mapping.default_company_id ?? "—"}
                    </dd>
                  </div>
                </dl>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Compañías permitidas
                  </p>
                  {allowedCompanies.length > 0 ? (
                    <ul className="mt-1 list-inside list-disc text-sm">
                      {allowedCompanies.map((c) => (
                        <li key={c.id}>
                          {c.name} <span className="text-muted-foreground">#{c.id}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-muted-foreground">
                      IDs: {mapping.allowed_company_ids.join(", ") || "—"}
                    </p>
                  )}
                </div>
                {mapping.last_verified_at && (
                  <p className="text-xs text-muted-foreground">
                    Última verificación:{" "}
                    {new Date(mapping.last_verified_at).toLocaleString("es-DO")}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Usuario JAIOS</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p>{me?.jaios_name}</p>
            <p>{me?.jaios_email}</p>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
