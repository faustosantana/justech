"use client";

import Link from "next/link";
import { Building2, ExternalLink, Upload } from "lucide-react";
import { useMemo, useState } from "react";

import { MutateButton } from "@/components/permissions/mutate-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import { apiClient } from "@/lib/api";
import { COMPANY_LABELS, type OpportunityCompany } from "@/lib/dgcp";
import type { CompanyProfile } from "@/lib/settings";

const RPE_STORAGE_KEY = "jaios_dgcp_rpe_filter";
const COMPANY_STORAGE_KEY = "jaios_dgcp_company_filter";

const CANONICAL_COMPANIES: OpportunityCompany[] = [
  "justech",
  "just_office",
  "mf_plug_safe",
  "omni_solutions",
];

export function loadSavedRpeFilter(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(RPE_STORAGE_KEY) ?? "";
}

export function loadSavedCompanyFilter(): OpportunityCompany | "" {
  if (typeof window === "undefined") return "";
  const raw = localStorage.getItem(COMPANY_STORAGE_KEY) ?? "";
  return CANONICAL_COMPANIES.includes(raw as OpportunityCompany)
    ? (raw as OpportunityCompany)
    : "";
}

export function saveRpeFilter(rpe: string) {
  if (typeof window === "undefined") return;
  if (rpe) localStorage.setItem(RPE_STORAGE_KEY, rpe);
  else localStorage.removeItem(RPE_STORAGE_KEY);
}

export function saveCompanyFilter(company: OpportunityCompany | "") {
  if (typeof window === "undefined") return;
  if (company) localStorage.setItem(COMPANY_STORAGE_KEY, company);
  else localStorage.removeItem(COMPANY_STORAGE_KEY);
}

export function resolveCompanyFromRpe(
  rpe: string,
  profiles: CompanyProfile[],
): OpportunityCompany | "" {
  const needle = rpe.trim().toLowerCase();
  if (!needle) return "";
  const match = profiles.find((p) => (p.rpe ?? "").toLowerCase() === needle);
  const key = (match?.company_key || "") as OpportunityCompany;
  return CANONICAL_COMPANIES.includes(key) ? key : "";
}

function profileForCompany(
  companyKey: OpportunityCompany | "",
  profiles: CompanyProfile[],
): CompanyProfile | undefined {
  if (!companyKey) return undefined;
  return profiles.find((p) => p.company_key === companyKey);
}

interface DgcpRpeFilterBarProps {
  profiles: CompanyProfile[];
  companyValue: OpportunityCompany | "";
  rpeValue: string;
  onFilterChange: (company: OpportunityCompany | "", rpe: string) => void;
  onProfilesRefresh?: () => void;
}

export function DgcpRpeFilterBar({
  profiles,
  companyValue,
  rpeValue,
  onFilterChange,
  onProfilesRefresh,
}: DgcpRpeFilterBarProps) {
  const { access } = usePlatformAccess();
  const [associateOpen, setAssociateOpen] = useState(false);
  const [associateRpe, setAssociateRpe] = useState("");
  const [saving, setSaving] = useState(false);
  const [associateError, setAssociateError] = useState<string | null>(null);

  const selectedProfile = useMemo(
    () => profileForCompany(companyValue, profiles),
    [companyValue, profiles],
  );

  const rpeOptions = useMemo(
    () =>
      profiles
        .filter((p) => p.rpe?.trim())
        .map((p) => ({
          rpe: p.rpe!.trim(),
          company_key: p.company_key as OpportunityCompany,
          label: `${p.rpe} — ${p.razon_social ?? COMPANY_LABELS[p.company_key as OpportunityCompany] ?? p.company_key}`,
        })),
    [profiles],
  );

  function applyCompany(next: OpportunityCompany | "") {
    const profile = profileForCompany(next, profiles);
    const rpe = profile?.rpe?.trim() ?? (next === companyValue ? rpeValue : "");
    saveCompanyFilter(next);
    saveRpeFilter(rpe);
    onFilterChange(next, rpe);
  }

  function applyRpe(next: string) {
    const company = resolveCompanyFromRpe(next, profiles) || companyValue;
    saveRpeFilter(next);
    if (company) saveCompanyFilter(company);
    onFilterChange(company, next);
  }

  function clearFilters() {
    saveCompanyFilter("");
    saveRpeFilter("");
    onFilterChange("", "");
  }

  async function saveAssociatedRpe() {
    if (!selectedProfile?.id) return;
    const value = associateRpe.trim();
    if (!value) {
      setAssociateError("Ingrese un número de RPE válido.");
      return;
    }
    setSaving(true);
    setAssociateError(null);
    try {
      await apiClient.updateDocumentsHubField(selectedProfile.id, "proveedor_estado", value);
      saveRpeFilter(value);
      onFilterChange(companyValue, value);
      onProfilesRefresh?.();
      setAssociateOpen(false);
    } catch {
      setAssociateError("No se pudo guardar el RPE. Verifique permisos de documentos.");
    } finally {
      setSaving(false);
    }
  }

  const profileHref = selectedProfile?.id
    ? `/apps/empresas-grupo/perfil/${selectedProfile.id}`
    : "/apps/empresas-grupo/empresas";

  const unresolvedRpe = rpeValue.trim() && !resolveCompanyFromRpe(rpeValue, profiles);

  return (
    <div className="rounded-lg border border-primary/25 bg-primary/5 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-primary" />
        <p className="text-sm font-medium">Empresa del grupo y RPE</p>
      </div>
      <p className="text-xs text-muted-foreground">
        Usa <strong>Todas las empresas</strong> / <strong>Todos los RPE</strong> para ver procesos
        abiertos del portal sin restringir por un solo RPE. Luego filtra por empresa si quieres
        ver solo las que encajan con un RPE concreto.
      </p>

      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1 min-w-[200px]">
          <Label htmlFor="dgcp-company-select" className="text-xs">
            Empresa
          </Label>
          <select
            id="dgcp-company-select"
            className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
            value={companyValue}
            onChange={(e) => applyCompany((e.target.value || "") as OpportunityCompany | "")}
          >
            <option value="">Todas las empresas</option>
            {CANONICAL_COMPANIES.map((key) => (
              <option key={key} value={key}>
                {COMPANY_LABELS[key]}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1 min-w-[220px]">
          <Label htmlFor="dgcp-rpe-select" className="text-xs">
            RPE registrado
          </Label>
          <select
            id="dgcp-rpe-select"
            className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
            value={rpeOptions.some((o) => o.rpe === rpeValue) ? rpeValue : ""}
            onChange={(e) => applyRpe(e.target.value)}
          >
            <option value="">Todos los RPE</option>
            {rpeOptions.map((opt) => (
              <option key={opt.rpe} value={opt.rpe}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1 min-w-[160px]">
          <Label htmlFor="dgcp-rpe-manual" className="text-xs">
            O escriba RPE
          </Label>
          <Input
            id="dgcp-rpe-manual"
            placeholder="Ej. 77671"
            value={rpeValue}
            onChange={(e) => applyRpe(e.target.value)}
            className="h-9"
          />
        </div>

        {(companyValue || rpeValue) && (
          <button
            type="button"
            className="text-xs text-primary hover:underline pb-2"
            onClick={clearFilters}
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {companyValue && selectedProfile && (
        <div className="rounded-md border bg-background/80 p-3 text-sm space-y-2">
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
            <span>
              <span className="text-muted-foreground">RNC:</span>{" "}
              {selectedProfile.rnc?.trim() || "—"}
            </span>
            <span>
              <span className="text-muted-foreground">RPE:</span>{" "}
              {selectedProfile.rpe?.trim() || "No registrado"}
            </span>
            <span>
              <span className="text-muted-foreground">Perfil:</span>{" "}
              {selectedProfile.completeness_score ?? 0}% completo
            </span>
          </div>

          {!selectedProfile.rpe?.trim() ? (
            <div className="space-y-2">
              <p className="text-xs text-warning">
                Esta empresa no tiene RPE registrado. Asócielo aquí o desde el perfil
                empresarial.
              </p>
              <div className="flex flex-wrap gap-2">
                <MutateButton
                  permission="mutate_documents"
                  access={access}
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setAssociateRpe(rpeValue);
                    setAssociateError(null);
                    setAssociateOpen(true);
                  }}
                >
                  Asociar RPE
                </MutateButton>
                <Button size="sm" variant="outline" asChild>
                  <Link href={profileHref}>
                    <Upload className="mr-1.5 h-3.5 w-3.5" />
                    Subir RPE
                  </Link>
                </Button>
                <Button size="sm" variant="ghost" asChild>
                  <Link href={profileHref}>
                    Ir al perfil empresarial
                    <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
                  </Link>
                </Button>
              </div>
            </div>
          ) : (
            <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" asChild>
              <Link href={profileHref}>
                Ver perfil y documentos legales
                <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
              </Link>
            </Button>
          )}
        </div>
      )}

      {unresolvedRpe && (
        <div className="rounded-md border border-warning/40 bg-warning/5 p-3 space-y-2">
          <p className="text-xs text-warning">
            RPE «{rpeValue}» no está vinculado a ninguna empresa. Asócielo a una empresa
            existente o créelo en el perfil empresarial.
          </p>
          <div className="flex flex-wrap gap-2">
            <div className="space-y-1 min-w-[180px]">
              <Label htmlFor="dgcp-rpe-bind-company" className="text-xs">
                Asociar a empresa
              </Label>
              <select
                id="dgcp-rpe-bind-company"
                className="h-8 w-full rounded-md border border-border bg-background px-2 text-xs"
                value={companyValue}
                onChange={(e) => {
                  const c = (e.target.value || "") as OpportunityCompany | "";
                  applyCompany(c);
                  if (c) {
                    setAssociateRpe(rpeValue);
                    setAssociateError(null);
                    setAssociateOpen(true);
                  }
                }}
              >
                <option value="">Seleccione empresa…</option>
                {CANONICAL_COMPANIES.map((key) => (
                  <option key={key} value={key}>
                    {COMPANY_LABELS[key]}
                  </option>
                ))}
              </select>
            </div>
            <Button size="sm" variant="outline" className="self-end" asChild>
              <Link href="/apps/empresas-grupo/empresas">Ir a Empresas del Grupo</Link>
            </Button>
          </div>
        </div>
      )}

      {associateOpen && companyValue && (
        <div className="rounded-md border bg-background p-4 space-y-3">
          <p className="text-sm font-medium">
            Asociar RPE a {COMPANY_LABELS[companyValue]}
          </p>
          <div className="space-y-2">
            <Label htmlFor="associate-rpe">Número RPE</Label>
            <Input
              id="associate-rpe"
              value={associateRpe}
              onChange={(e) => setAssociateRpe(e.target.value)}
              placeholder="Ej. 77671"
            />
            {associateError && (
              <p className="text-xs text-destructive">{associateError}</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setAssociateOpen(false)}>
              Cancelar
            </Button>
            <MutateButton
              permission="mutate_documents"
              access={access}
              size="sm"
              onClick={() => void saveAssociatedRpe()}
              disabled={saving}
            >
              {saving ? "Guardando…" : "Guardar RPE"}
            </MutateButton>
          </div>
        </div>
      )}
    </div>
  );
}
