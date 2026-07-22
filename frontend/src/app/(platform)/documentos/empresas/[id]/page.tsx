import { redirect } from "next/navigation";

export default async function DocumentosEmpresasRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/apps/empresas-grupo/perfil/${id}`);
}
