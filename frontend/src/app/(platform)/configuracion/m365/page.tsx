import { redirect } from "next/navigation";

export default function M365ConfigRedirect() {
  redirect("/configuracion/integraciones/microsoft365");
}
