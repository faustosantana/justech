/** Etiqueta visible del contexto del Assistant según ruta y registro activo. */

export function assistantContextLabel(
  pathname: string,
  recordType?: string | null,
  recordId?: string | null,
): string {
  if (recordType === "dgcp" || recordType === "dgcp_opportunity") {
    if (recordId) {
      return `DGCP — proceso ${recordId.slice(0, 8)}…`;
    }
    return "DGCP";
  }
  if (recordType === "customer") return "Odoo — cliente";
  if (recordType === "invoice") return "Odoo — factura";
  if (recordType === "product") return "Odoo — producto";

  if (pathname.startsWith("/prices")) return "Inteligencia de Precios";
  if (pathname.startsWith("/documents")) return "Documentos";
  if (pathname.startsWith("/odoo")) return "Odoo";
  if (pathname.startsWith("/tasks")) return "Tareas";
  if (pathname.startsWith("/work")) return "Centro de trabajo";
  if (pathname.startsWith("/dgcp")) return "DGCP";
  if (pathname.startsWith("/search")) return "Búsqueda empresarial";
  if (pathname.startsWith("/dashboard")) return "Panel principal";
  if (pathname.startsWith("/m365")) return "Microsoft 365";
  if (pathname.startsWith("/admin")) return "Administración";
  if (pathname.startsWith("/notifications")) return "Notificaciones";
  return "JAIOS";
}
