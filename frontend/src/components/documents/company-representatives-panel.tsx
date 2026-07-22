"use client";

import { Loader2, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { RepresentativeCard } from "@/components/documents/representative-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import type { CompanyRepresentative, RepresentativeCreatePayload } from "@/lib/company-representatives";
import { RELATION_TYPES } from "@/lib/company-representatives";

const EMPTY_FORM: RepresentativeCreatePayload = {
  full_name: "",
  identification_type: "cedula",
  identification_number: "",
  position: "",
  relation_type: "representante_legal",
  email: "",
  phone: "",
  can_sign: false,
  is_legal_representative: false,
  can_participate_in_bids: true,
};

export function CompanyRepresentativesPanel({
  companyId,
  onChanged,
  documentTypes,
  showAddButton = true,
  title = "Representantes y firmantes",
}: {
  companyId: string;
  onChanged?: () => void;
  documentTypes?: string[];
  showAddButton?: boolean;
  title?: string;
}) {
  const [reps, setReps] = useState<CompanyRepresentative[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<RepresentativeCreatePayload>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getCompanyRepresentatives(companyId);
      setReps(res.representatives);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los representantes.");
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = async () => {
    await load();
    onChanged?.();
  };

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormOpen(true);
  };

  const openEdit = (rep: CompanyRepresentative) => {
    setEditingId(rep.id);
    setForm({
      full_name: rep.full_name,
      identification_type: rep.identification_type,
      identification_number: rep.identification_number ?? "",
      position: rep.position ?? "",
      relation_type: rep.relation_type,
      email: rep.email ?? "",
      phone: rep.phone ?? "",
      can_sign: rep.can_sign,
      is_legal_representative: rep.is_legal_representative,
      can_participate_in_bids: rep.can_participate_in_bids,
    });
    setFormOpen(true);
  };

  const [duplicateMatch, setDuplicateMatch] = useState<CompanyRepresentative | null>(null);

  const saveRepresentative = async (forceNew = false) => {
    if (!form.full_name.trim()) {
      setError("Indique el nombre completo.");
      return;
    }
    setSaving(true);
    setError(null);
    setDuplicateMatch(null);
    try {
      if (editingId) {
        await apiClient.updateCompanyRepresentative(companyId, editingId, form);
      } else {
        await apiClient.createCompanyRepresentative(companyId, form, forceNew);
      }
      setFormOpen(false);
      await refresh();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "No se pudo guardar el representante.";
      setError(msg);
      if (!editingId && msg.includes("ya existe")) {
        const match = reps.find(
          (r) => r.full_name.toLowerCase() === form.full_name.trim().toLowerCase(),
        );
        if (match) setDuplicateMatch(match);
      }
    } finally {
      setSaving(false);
    }
  };

  const assignRoleToExisting = async () => {
    if (!duplicateMatch || !form.relation_type) return;
    setSaving(true);
    setError(null);
    try {
      await apiClient.assignCompanyPersonRole(
        companyId,
        duplicateMatch.id,
        form.relation_type,
        form.can_sign,
      );
      setDuplicateMatch(null);
      setFormOpen(false);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo agregar el rol.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <p className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando representantes…
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground">
            {reps.length} representante(s) registrado(s) · acciones por persona y documento
          </p>
        </div>
        {showAddButton && (
          <Button size="sm" onClick={openCreate}>
            <Plus className="mr-1 h-4 w-4" />
            Agregar representante
          </Button>
        )}
      </div>

      {error && !formOpen && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">{error}</p>
      )}

      {reps.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">No hay representantes registrados.</p>
            {showAddButton && (
              <Button size="sm" className="mt-3" onClick={openCreate}>
                <Plus className="mr-1 h-4 w-4" />
                Agregar representante
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {reps.map((rep) => (
        <RepresentativeCard
          key={rep.id}
          companyId={companyId}
          rep={rep}
          onEdit={openEdit}
          onChanged={() => void refresh()}
          documentTypes={documentTypes}
        />
      ))}

      {formOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="max-h-[90vh] w-full max-w-lg overflow-y-auto">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{editingId ? "Editar representante" : "Agregar representante"}</CardTitle>
              <button type="button" onClick={() => setFormOpen(false)}>
                <X className="h-5 w-5" />
              </button>
            </CardHeader>
            <CardContent className="space-y-3">
              {error && <p className="text-sm text-amber-800">{error}</p>}
              <Input
                placeholder="Nombre completo *"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
              <Input
                placeholder="Cédula / Pasaporte"
                value={form.identification_number}
                onChange={(e) => setForm({ ...form, identification_number: e.target.value })}
              />
              <Input
                placeholder="Cargo"
                value={form.position}
                onChange={(e) => setForm({ ...form, position: e.target.value })}
              />
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={form.relation_type}
                onChange={(e) => setForm({ ...form, relation_type: e.target.value })}
              >
                {RELATION_TYPES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
              <Input
                placeholder="Correo"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
              <Input
                placeholder="Teléfono"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.can_sign}
                  onChange={(e) => setForm({ ...form, can_sign: e.target.checked })}
                />
                Puede firmar documentos
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_legal_representative}
                  onChange={(e) => setForm({ ...form, is_legal_representative: e.target.checked })}
                />
                Es representante legal
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.can_participate_in_bids}
                  onChange={(e) => setForm({ ...form, can_participate_in_bids: e.target.checked })}
                />
                Participa en licitaciones
              </label>
              {duplicateMatch && (
                <div className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-3 text-sm">
                  <p>
                    <strong>{duplicateMatch.full_name}</strong> ya existe. ¿Agregarle el rol{" "}
                    {RELATION_TYPES.find((r) => r.value === form.relation_type)?.label ?? form.relation_type}?
                  </p>
                  <div className="mt-2 flex gap-2">
                    <Button size="sm" onClick={() => void assignRoleToExisting()} disabled={saving}>
                      Sí, agregar rol
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => void saveRepresentative(true)}
                      disabled={saving}
                    >
                      No, crear nueva persona
                    </Button>
                  </div>
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="ghost" onClick={() => setFormOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={() => void saveRepresentative()} disabled={saving}>
                  {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
                  Guardar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
