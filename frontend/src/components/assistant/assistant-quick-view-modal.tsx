"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AssistantActionButtons } from "@/components/assistant/assistant-action-buttons";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import type { QuickViewTarget } from "@/lib/assistant-types";
import { buildQuickViewActions } from "@/lib/assistant-quick-view";
import { cn } from "@/lib/utils";

interface AssistantQuickViewModalProps {
  target: QuickViewTarget | null;
  onClose: () => void;
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="grid grid-cols-[minmax(0,34%)_1fr] gap-2 border-b border-border/60 py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="break-words font-medium">{String(value)}</span>
    </div>
  );
}

export function AssistantQuickViewModal({ target, onClose }: AssistantQuickViewModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<{ label: string; value: string }[]>([]);
  const [title, setTitle] = useState("");
  const [externalUrl, setExternalUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!target) {
      setFields([]);
      setTitle("");
      setError(null);
      setExternalUrl(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const result = await loadQuickView(target);
        if (!cancelled) {
          setTitle(result.title);
          setFields(result.fields);
          setExternalUrl(result.externalUrl ?? null);
        }
      } catch {
        if (!cancelled) {
          setError("No pude cargar el detalle. Intenta abrir en JAIOS.");
          setTitle(target.label || target.entity_type);
          setFields([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [target]);

  if (!target) return null;

  const actions = buildQuickViewActions(target.entity_type, target.entity_id);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        aria-label="Cerrar vista rápida"
        onClick={onClose}
      />
      <div
        className={cn(
          "relative z-[71] flex max-h-[85vh] w-full max-w-lg flex-col",
          "rounded-xl border border-border bg-card shadow-2xl",
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="quick-view-title"
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 id="quick-view-title" className="truncate pr-2 text-sm font-semibold">
            {title || "Vista rápida"}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Cerrar">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3">
          {loading && <p className="text-sm text-muted-foreground animate-pulse">Cargando…</p>}
          {error && <p className="break-words text-sm text-destructive">{error}</p>}
          {!loading &&
            fields.map((f) => <Field key={f.label} label={f.label} value={f.value} />)}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-3">
          <AssistantActionButtons actions={actions} onQuickView={() => {}} />
          <div className="flex flex-wrap gap-2">
            {actions[0]?.url && (
              <Link href={actions[0].url} className="text-xs text-primary hover:underline" onClick={onClose}>
                Abrir en JAIOS →
              </Link>
            )}
            {externalUrl && (
              <a
                href={externalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline"
              >
                Ver en Odoo ↗
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

async function loadQuickView(
  target: QuickViewTarget,
): Promise<{ title: string; fields: { label: string; value: string }[]; externalUrl?: string | null }> {
  const { entity_type, entity_id } = target;

  if (entity_type === "product") {
    const d = await apiClient.getOdooProductDetail(Number(entity_id));
    return {
      title: d.name,
      fields: [
        { label: "Código", value: d.default_code || "—" },
        { label: "Último precio", value: String(d.last_price ?? "—") },
        { label: "Precio promedio", value: String(d.average_price ?? "—") },
        { label: "Costo estándar", value: String(d.standard_price ?? "—") },
        { label: "Margen est.", value: d.estimated_margin_pct != null ? `${d.estimated_margin_pct}%` : "—" },
      ],
    };
  }

  if (entity_type === "customer") {
    const d = await apiClient.getOdooCustomerDetail(Number(entity_id));
    return {
      title: d.name,
      fields: [
        { label: "Ventas históricas", value: String(d.total_sales_historical) },
        { label: "Pendiente", value: String(d.total_due) },
        { label: "Vencido", value: String(d.total_overdue) },
        { label: "Facturas abiertas", value: String(d.open_invoices.length) },
        { label: "Cotizaciones", value: String(d.quotations.length) },
      ],
    };
  }

  if (entity_type === "invoice") {
    const d = await apiClient.getOdooInvoiceDetail(Number(entity_id));
    return {
      title: d.name,
      externalUrl: d.odoo_url ?? null,
      fields: [
        { label: "Cliente", value: d.partner_name },
        { label: "Total", value: String(d.amount_total) },
        { label: "Pendiente", value: String(d.amount_residual) },
        { label: "Estado", value: d.payment_state || d.state || "—" },
        { label: "Vence", value: d.due_date || "—" },
      ],
    };
  }

  if (entity_type === "vendor") {
    const d = await apiClient.getOdooVendorDetail(Number(entity_id));
    return {
      title: d.name,
      fields: [
        { label: "Compras totales", value: String(d.total_purchase_value) },
        { label: "Pedidos", value: String(d.purchase_orders?.length ?? 0) },
        { label: "Email", value: d.email || "—" },
      ],
    };
  }

  if (entity_type === "dgcp") {
    const d = await apiClient.getDGCPOpportunity(entity_id);
    return {
      title: d.code,
      fields: [
        { label: "Título", value: d.title },
        { label: "Institución", value: d.institution },
        { label: "Monto", value: String(d.amount) },
        { label: "Vence", value: String(d.deadline) },
        { label: "Estado", value: d.status },
      ],
    };
  }

  if (entity_type === "task") {
    const d = await apiClient.getTask(entity_id);
    return {
      title: d.title,
      fields: [
        { label: "Estado", value: d.status },
        { label: "Prioridad", value: d.priority },
        { label: "Asignado", value: d.assigned_to_name || d.suggested_assignee_name || "—" },
        { label: "Vence", value: d.due_date ? String(d.due_date) : "—" },
        { label: "Departamento", value: d.department || "—" },
      ],
    };
  }

  return { title: entity_type, fields: [{ label: "ID", value: entity_id }] };
}
