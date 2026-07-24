import { redirect } from "next/navigation";

/** Legacy “Estadísticas” → Matriz avanzada. */
export default function LegacyStatisticsRedirect() {
  redirect("/lottery/admin/control-center/motor/combinaciones");
}
