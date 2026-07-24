import { redirect } from "next/navigation";

/** Legacy “Consulta histórica” → Historial del Número. */
export default function LegacySearchRedirect() {
  redirect("/lottery/admin/control-center/motor/historial-numero");
}
