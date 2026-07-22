"use client";

import { ChevronDown } from "lucide-react";
import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";

export const ENTERPRISE_SOURCE_OPTIONS: { id: string; label: string }[] = [
  { id: "odoo", label: "Odoo / ERP" },
  { id: "dgcp", label: "DGCP" },
  { id: "jaios", label: "JAIOS" },
  { id: "documents", label: "Documentos" },
  { id: "knowledge", label: "Base de Inteligencia" },
  { id: "prices", label: "Listas de Precios" },
  { id: "suppliers", label: "Proveedores" },
  { id: "ingram", label: "Ingram" },
  { id: "omega", label: "Omega" },
  { id: "intcomex", label: "Intcomex" },
  { id: "cecomsa", label: "Cecomsa" },
  { id: "tecnosinergia", label: "Tecnosinergia" },
  { id: "cenicsa", label: "CENICSA" },
  { id: "tecnomarket", label: "Tecnomarket" },
  { id: "m365", label: "Microsoft 365" },
];

export const ALL_ENTERPRISE_SOURCE_IDS = ENTERPRISE_SOURCE_OPTIONS.map((o) => o.id);

/** Vacío = consultar todas las fuentes (sin filtro en API). */
export function isAllSourcesSelected(selected: string[]): boolean {
  return selected.length === 0 || selected.length === ALL_ENTERPRISE_SOURCE_IDS.length;
}

export function sourcesForApi(selected: string[]): string[] | undefined {
  if (isAllSourcesSelected(selected)) return undefined;
  return selected;
}

interface SourceMultiSelectProps {
  selected: string[];
  onChange: (next: string[]) => void;
  className?: string;
}

export function SourceMultiSelect({ selected, onChange, className }: SourceMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const allSelected = isAllSourcesSelected(selected);

  const summary = useMemo(() => {
    if (allSelected) return "Todas las fuentes";
    if (selected.length === 0) return "Ninguna fuente";
    if (selected.length <= 2) {
      return ENTERPRISE_SOURCE_OPTIONS.filter((o) => selected.includes(o.id))
        .map((o) => o.label)
        .join(" + ");
    }
    return `${selected.length} fuentes`;
  }, [allSelected, selected]);

  const toggleAll = () => {
    if (allSelected) {
      onChange([]);
    } else {
      onChange([...ALL_ENTERPRISE_SOURCE_IDS]);
    }
  };

  const toggleOne = (id: string) => {
    if (allSelected) {
      onChange(ALL_ENTERPRISE_SOURCE_IDS.filter((s) => s !== id));
      return;
    }
    const has = selected.includes(id);
    if (has) {
      onChange(selected.filter((s) => s !== id));
      return;
    }
    const next = [...selected, id];
    if (next.length === ALL_ENTERPRISE_SOURCE_IDS.length) {
      onChange([...ALL_ENTERPRISE_SOURCE_IDS]);
    } else {
      onChange(next);
    }
  };

  return (
    <div className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-full items-center justify-between rounded-md border border-border bg-background px-3 text-left text-sm"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="truncate">{summary}</span>
        <ChevronDown className={cn("ml-2 h-4 w-4 shrink-0 opacity-60 transition", open && "rotate-180")} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" aria-hidden onClick={() => setOpen(false)} />
          <div
            className="absolute left-0 right-0 z-50 mt-1 max-h-72 overflow-y-auto rounded-md border border-border bg-popover p-2 shadow-md"
            role="listbox"
            aria-multiselectable
          >
            <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted/60">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleAll}
                className="rounded border-border"
              />
              <span className="font-medium">Todas las fuentes</span>
            </label>
            <div className="my-1 border-t border-border/60" />
            {ENTERPRISE_SOURCE_OPTIONS.map((opt) => {
              const checked = allSelected || selected.includes(opt.id);
              return (
                <label
                  key={opt.id}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted/60"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleOne(opt.id)}
                    className="rounded border-border"
                  />
                  <span>{opt.label}</span>
                </label>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
