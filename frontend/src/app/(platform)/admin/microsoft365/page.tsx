import { redirect } from "next/navigation";

export default function AdminLegacyRedirectPage() {
  redirect("/configuracion/integraciones/microsoft365");
}
