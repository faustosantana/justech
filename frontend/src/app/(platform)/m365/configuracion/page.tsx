import { redirect } from "next/navigation";

/** Alias /m365/configuracion → pestaña Configuración */
export default function M365ConfiguracionPage() {
  redirect("/m365?tab=configuracion");
}
