"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api";
import type { CompanyRepresentative } from "@/lib/company-representatives";

const PROFILE_PERSON_FIELDS = new Set([
  "representante_legal",
  "responsable_legal",
  "responsable_financiero",
  "responsable_licitaciones",
]);

export function isProfilePersonField(fieldKey: string): boolean {
  return PROFILE_PERSON_FIELDS.has(fieldKey);
}

export function CompanyPersonSelect({
  companyId,
  fieldKey,
  fieldLabel,
  currentValue,
  onLinked,
}: {
  companyId: string;
  fieldKey: string;
  fieldLabel: string;
  currentValue?: string | null;
  onLinked?: (message: string) => void;
}) {
  const [people, setPeople] = useState<CompanyRepresentative[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const fn = apiClient.getCompanyRepresentatives;
    if (typeof fn !== "function") {
      setPeople([]);
      setError("La función de representantes no está disponible en este build.");
      setLoading(false);
      return;
    }
    fn(companyId)
      .then((res) => setPeople(Array.isArray(res?.representatives) ? res.representatives : []))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Error al cargar personas"))
      .finally(() => setLoading(false));
  }, [companyId]);

  useEffect(() => {
    load();
  }, [load]);

  const selectPerson = async (personId: string) => {
    setActing(true);
    setError(null);
    try {
      const res = await apiClient.linkCompanyProfilePerson(companyId, fieldKey, personId);
      onLinked?.(res.message);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo asignar la persona.");
    } finally {
      setActing(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground">Cargando personas relacionadas…</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Seleccione una persona ya registrada para «{fieldLabel}» sin duplicar datos.
      </p>
      {currentValue && <p className="text-sm">Actual: {currentValue}</p>}
      {error && <p className="text-sm text-amber-800">{error}</p>}
      <div className="flex flex-wrap gap-2">
        {people.map((p) => (
          <Button
            key={p.id}
            size="sm"
            variant="outline"
            disabled={acting}
            onClick={() => void selectPerson(p.id)}
          >
            {p.full_name}
            {p.role_labels?.length ? ` (${p.role_labels.join(", ")})` : ""}
          </Button>
        ))}
      </div>
    </div>
  );
}
