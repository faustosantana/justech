"use client";

import { ClipboardList } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";

interface CreateTaskButtonProps {
  eventType: string;
  title: string;
  description?: string;
  customerName?: string;
  odooCustomerId?: number;
  odooInvoiceId?: number;
  odooQuotationId?: number;
  dgcpProcessId?: string;
  source?: string;
  label?: string;
  variant?: "default" | "outline" | "secondary";
}

export function CreateTaskButton({
  eventType,
  title,
  description = "",
  customerName,
  odooCustomerId,
  odooInvoiceId,
  odooQuotationId,
  dgcpProcessId,
  source = "manual",
  label = "Crear tarea",
  variant = "outline",
}: CreateTaskButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    setLoading(true);
    try {
      const task = await apiClient.createTaskFromEvent({
        source,
        event_type: eventType,
        title,
        description,
        customer_name: customerName,
        odoo_customer_id: odooCustomerId,
        odoo_invoice_id: odooInvoiceId,
        odoo_quotation_id: odooQuotationId,
        dgcp_process_id: dgcpProcessId,
        apply_routing: true,
      });
      router.push(`/tasks/${task.id}`);
    } catch {
      alert("No se pudo crear la tarea. Intenta desde /tasks.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button variant={variant} size="sm" onClick={handleCreate} disabled={loading}>
      <ClipboardList className="mr-2 h-4 w-4" />
      {loading ? "Creando…" : label}
    </Button>
  );
}
