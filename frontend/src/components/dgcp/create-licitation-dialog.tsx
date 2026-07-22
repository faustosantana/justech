"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { MutateButton } from "@/components/permissions/mutate-button";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import type { PlatformAccess } from "@/lib/admin";
import type { OpportunityCompany, OpportunityStatus } from "@/lib/dgcp";

interface Props {
  onCreated?: (id: string) => void;
  access?: PlatformAccess | null;
}

export function CreateLicitationDialog({ onCreated, access = null }: Props) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    code: "",
    institution: "",
    title: "",
    amount: "",
    deadline: "",
    modalidad: "",
    source_url: "",
    company: "unclassified" as OpportunityCompany,
    status: "detected" as OpportunityStatus,
    description: "",
  });

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const opp = await apiClient.createDGCPOpportunity({
        ...form,
        amount: form.amount || "0",
        currency: "DOP",
        source: "manual",
      });
      setOpen(false);
      onCreated?.(opp.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al crear");
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <MutateButton permission="mutate_dgcp" access={access} size="sm" onClick={() => setOpen(true)}>
        <Plus className="mr-1 h-3.5 w-3.5" />
        Nueva licitación
      </MutateButton>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl border bg-background p-4 shadow-lg space-y-3">
        <h3 className="font-semibold">Crear licitación manual</h3>
        <div className="grid gap-2 sm:grid-cols-2">
          {(
            [
              ["code", "Código proceso"],
              ["institution", "Entidad contratante"],
              ["title", "Objeto / título"],
              ["amount", "Monto estimado"],
              ["deadline", "Fecha límite"],
              ["modalidad", "Modalidad"],
              ["source_url", "URL fuente"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="text-xs space-y-0.5">
              <span className="text-muted-foreground">{label}</span>
              <input
                type={key === "deadline" ? "date" : key === "amount" ? "number" : "text"}
                className="w-full rounded border px-2 py-1.5 text-sm"
                value={form[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              />
            </label>
          ))}
        </div>
        <label className="text-xs block space-y-0.5">
          <span className="text-muted-foreground">Descripción</span>
          <textarea
            className="w-full rounded border px-2 py-1.5 text-sm min-h-[60px]"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
        </label>
        {error && <p className="text-xs text-destructive">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button size="sm" disabled={saving || !form.code || !form.institution || !form.title || !form.deadline} onClick={() => void submit()}>
            {saving ? "Guardando…" : "Crear expediente"}
          </Button>
        </div>
      </div>
    </div>
  );
}
