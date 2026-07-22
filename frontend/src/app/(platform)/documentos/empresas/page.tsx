import { redirect } from "next/navigation";

export default function DocumentosEmpresasListRedirect() {
  redirect("/apps/empresas-grupo/empresas");
}
