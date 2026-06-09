"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Building2, Check, ChevronDown, Layers, Settings, Shield } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useCompanyContext } from "@/lib/company-context";
import { cn } from "@/lib/utils";

export function CompanySelector({ compact = false }: { compact?: boolean }) {
  const { context, loading, setSelection, scopeLabel } = useCompanyContext();
  const [open, setOpen] = useState(false);
  const [multiOpen, setMultiOpen] = useState(false);
  const [picked, setPicked] = useState<number[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);

  const companies = context?.allowed_companies ?? [];

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  if (loading) {
    return (
      <div className="h-9 w-44 animate-pulse rounded-lg border border-border bg-muted/50" aria-hidden />
    );
  }

  if (!context?.odoo_connected || companies.length === 0) {
    return (
      <span className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs text-muted-foreground">
        <Building2 className="h-3.5 w-3.5" />
        {scopeLabel}
      </span>
    );
  }

  const mode = context.selection_mode;
  const activeId = context.active_company_id || context.selected_company_ids[0];
  const activeName =
    mode === "all"
      ? "Todas las empresas"
      : mode === "multi"
        ? `${context.selected_company_ids.length} empresas`
        : companies.find((c) => c.id === activeId)?.name || scopeLabel;

  async function applySingle(id: number) {
    await setSelection({
      selection_mode: "single",
      active_company_id: id,
      selected_company_ids: [id],
    });
    setOpen(false);
    setMultiOpen(false);
  }

  async function applyAll() {
    await setSelection({
      selection_mode: "all",
      selected_company_ids: companies.map((c) => c.id),
    });
    setOpen(false);
    setMultiOpen(false);
  }

  async function applyMulti() {
    if (picked.length === 0) return;
    await setSelection({
      selection_mode: "multi",
      active_company_id: picked[0],
      selected_company_ids: picked,
    });
    setOpen(false);
    setMultiOpen(false);
  }

  return (
    <div ref={rootRef} className={cn("relative", compact ? "" : "w-full max-w-xs")}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-9 min-w-[200px] max-w-[260px] items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 text-left text-sm font-medium text-foreground shadow-sm transition hover:border-primary/30 hover:bg-accent/50"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="flex min-w-0 items-center gap-2">
          <Building2 className="h-4 w-4 shrink-0 text-primary" />
          <span className="truncate">{activeName}</span>
        </span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition", open && "rotate-180")} />
      </button>

      {open && (
        <div className="company-menu" role="listbox">
          <div className="border-b border-border px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Empresa activa</p>
          </div>

          {companies.map((c) => {
            const selected = mode === "single" && activeId === c.id;
            return (
              <button
                key={c.id}
                type="button"
                role="option"
                aria-selected={selected}
                className="flex w-full items-center gap-2 px-3 py-2.5 text-sm hover:bg-accent/60"
                onClick={() => applySingle(c.id)}
              >
                <Check className={cn("h-4 w-4 text-primary", !selected && "opacity-0")} />
                <span className="truncate">{c.name}</span>
              </button>
            );
          })}

          {context.can_select_all && (
            <>
              <div className="my-1 border-t border-border" />
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2.5 text-sm hover:bg-accent/60"
                onClick={applyAll}
              >
                <Check className={cn("h-4 w-4 text-primary", mode !== "all" && "opacity-0")} />
                <Layers className="h-4 w-4 text-muted-foreground" />
                Todas las empresas
              </button>
            </>
          )}

          {companies.length > 1 && (
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2.5 text-sm hover:bg-accent/60"
              onClick={() => {
                setPicked(
                  context.selected_company_ids.length
                    ? [...context.selected_company_ids]
                    : ([companies[0]?.id].filter(Boolean) as number[]),
                );
                setMultiOpen(true);
                setOpen(false);
              }}
            >
              <Check className={cn("h-4 w-4 text-primary", mode !== "multi" && "opacity-0")} />
              Varias empresas…
            </button>
          )}

          <div className="my-1 border-t border-border" />
          <Link
            href="/configuracion"
            className="flex items-center gap-2 px-3 py-2.5 text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            onClick={() => setOpen(false)}
          >
            <Shield className="h-4 w-4" />
            Administrar permisos
          </Link>
          <Link
            href="/configuracion"
            className="flex items-center gap-2 px-3 py-2.5 text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            onClick={() => setOpen(false)}
          >
            <Settings className="h-4 w-4" />
            Configuración
          </Link>
        </div>
      )}

      {multiOpen && (
        <div className="company-menu left-0 right-auto mt-2 w-[300px] p-3">
          <p className="mb-2 text-xs font-semibold text-foreground">Selecciona empresas</p>
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {companies.map((c) => (
              <label key={c.id} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-accent/50">
                <input
                  type="checkbox"
                  checked={picked.includes(c.id)}
                  onChange={(e) => {
                    setPicked((prev) =>
                      e.target.checked ? [...prev, c.id] : prev.filter((id) => id !== c.id),
                    );
                  }}
                />
                {c.name}
              </label>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <Button type="button" size="sm" onClick={applyMulti} disabled={picked.length === 0}>
              Aplicar
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setMultiOpen(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
