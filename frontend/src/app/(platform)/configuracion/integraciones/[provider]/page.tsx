"use client";

import { notFound } from "next/navigation";
import { use } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationForm } from "@/components/settings/integration-form";

const PROVIDERS: Record<string, { title: string; description: string }> = {
  openai: {
    title: "OpenAI",
    description: "API Key, base URL opcional y modelo por defecto (p. ej. gpt-4o)",
  },
  anthropic: {
    title: "Anthropic",
    description: "API Key y modelo Claude configurado en el tenant",
  },
  deepseek: {
    title: "DeepSeek / Huawei",
    description: "Proveedor alternativo — API Key, endpoint y modelo",
  },
  n8n: {
    title: "n8n Automations",
    description: "URL del webhook n8n y API Key para automatizaciones",
  },
  qdrant: {
    title: "Qdrant Vector DB",
    description: "Host, puerto y API Key del almacén vectorial",
  },
  smtp: {
    title: "SMTP Email",
    description: "Servidor de correo saliente para notificaciones y alertas",
  },
};

export default function IntegracionProviderPage({ params }: { params: Promise<{ provider: string }> }) {
  const { provider } = use(params);
  const meta = PROVIDERS[provider];
  if (!meta) notFound();

  return (
    <div>
      <AdminPageHeader title={meta.title} description={meta.description} />
      <IntegrationForm provider={provider} title={meta.title} />
    </div>
  );
}
