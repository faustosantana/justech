import { redirect } from "next/navigation";

/** Soft redirect: relaciones viven en el motor unificado. */
export default function LegacyNumericRelationsRedirect() {
  redirect("/lottery/admin/control-center/motor/relaciones");
}
