import { redirect } from "next/navigation";

/** Legacy “Comparar” → Comparador histórico. */
export default function LegacyCompareRedirect() {
  redirect("/lottery/admin/control-center/motor/comparador");
}
