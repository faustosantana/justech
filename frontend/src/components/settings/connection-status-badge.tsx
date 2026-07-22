import { cn } from "@/lib/utils";

export type IntegrationStatus =
  | "not_configured"
  | "configured"
  | "connected"
  | "credential_error"
  | "permission_missing"
  | "read_only"
  | "read_write";

const STATUS_META: Record<
  IntegrationStatus,
  { label: string; className: string }
> = {
  not_configured: { label: "No configurado", className: "bg-muted text-muted-foreground" },
  configured: { label: "Configurado", className: "bg-amber-500/10 text-amber-700" },
  connected: { label: "Conectado", className: "bg-success/10 text-success" },
  credential_error: { label: "Error de credenciales", className: "bg-destructive/10 text-destructive" },
  permission_missing: { label: "Falta permiso", className: "bg-amber-500/10 text-amber-800" },
  read_only: { label: "Solo lectura", className: "bg-blue-500/10 text-blue-700" },
  read_write: { label: "Lectura y escritura", className: "bg-success/10 text-success" },
};

export function ConnectionStatusBadge({
  status,
  connected,
  configured,
}: {
  status?: IntegrationStatus | string;
  connected?: boolean;
  configured?: boolean;
}) {
  let resolved: IntegrationStatus = "not_configured";
  if (status && status in STATUS_META) {
    resolved = status as IntegrationStatus;
  } else if (connected) {
    resolved = "connected";
  } else if (configured) {
    resolved = "configured";
  }

  const meta = STATUS_META[resolved];
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", meta.className)}>
      {meta.label}
    </span>
  );
}
