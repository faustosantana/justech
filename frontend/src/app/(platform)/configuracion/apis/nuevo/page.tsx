"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { DynamicConnectorForm } from "@/components/admin/dynamic-connector-form";
import { EndpointBuilder } from "@/components/admin/endpoint-builder";
import { TestConnectionPanel } from "@/components/admin/test-connection-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { ConnectorCreatePayload } from "@/lib/connectors";
import { WIZARD_STEPS } from "@/lib/connectors";
import { cn } from "@/lib/utils";

const INITIAL: ConnectorCreatePayload = {
  name: "",
  connector_type: "rest_api",
  auth_method: "api_key",
  base_url: "",
  config: { timeout: 30, header_name: "Authorization" },
  secrets: {},
  user_link_mode: "none",
  read_only: true,
  environment: "development",
  endpoints: [],
};

export default function NuevoConectorPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<ConnectorCreatePayload>(INITIAL);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const [testErr, setTestErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await apiClient.createConnector(form);
      setCreatedId(res.id);
      setStep(5);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el conector.");
    } finally {
      setSaving(false);
    }
  };

  const testBeforeSave = async () => {
    if (!createdId) {
      setTestErr("Guarde el conector primero para probar con credenciales almacenadas, o complete URL y credenciales.");
      return;
    }
    setTesting(true);
    setTestErr(null);
    try {
      const res = await apiClient.testConnector(createdId);
      setTestMsg(res.message);
      setPreview(res.response_preview || null);
    } catch (err) {
      setTestErr(err instanceof ApiError ? err.message : "Prueba fallida");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div>
      <AdminPageHeader
        title="Crear nuevo conector"
        description="Asistente paso a paso — sin editar código ni .env"
        action={
          <Button variant="outline" size="sm" asChild>
            <Link href="/configuracion/apis">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver
            </Link>
          </Button>
        }
      />

      <div className="mb-8 flex flex-wrap gap-2">
        {WIZARD_STEPS.map((label, i) => (
          <button
            key={label}
            type="button"
            onClick={() => i <= step && setStep(i)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              i === step ? "bg-primary text-primary-foreground" : i < step ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground",
            )}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {step === 0 && <DynamicConnectorForm value={form} onChange={setForm} />}
      {step === 1 && <DynamicConnectorForm value={form} onChange={setForm} />}
      {step === 2 && <EndpointBuilder endpoints={form.endpoints || []} onChange={(eps) => setForm({ ...form, endpoints: eps })} />}
      {step === 3 && (
        <TestConnectionPanel
          onTest={testBeforeSave}
          loading={testing}
          message={testMsg}
          error={testErr}
          preview={preview}
        />
      )}
      {step === 4 && (
        <Card>
          <CardContent className="space-y-3 py-6 text-sm">
            <p><strong>Nombre:</strong> {form.name}</p>
            <p><strong>URL:</strong> {form.base_url || "—"}</p>
            <p><strong>Modo:</strong> {form.read_only ? "Solo lectura" : "Lectura y escritura"}</p>
            <p><strong>Endpoints:</strong> {form.endpoints?.length || 0}</p>
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked />
              Disponible para usuarios (tras guardar)
            </label>
          </CardContent>
        </Card>
      )}
      {step === 5 && (
        <Card className="border-success/30 bg-success/5">
          <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
            <Check className="h-10 w-10 text-success" />
            <p className="text-lg font-medium">Conector creado</p>
            <div className="flex gap-2">
              {createdId && (
                <Button asChild>
                  <Link href={`/configuracion/apis/${createdId}`}>Ver conector</Link>
                </Button>
              )}
              <Button variant="outline" asChild>
                <Link href="/configuracion/apis">Lista de conectores</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-6 flex justify-between">
        <Button variant="outline" disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))}>
          Anterior
        </Button>
        {step < 4 && (
          <Button onClick={() => setStep((s) => s + 1)}>
            Siguiente
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        )}
        {step === 4 && (
          <Button onClick={save} disabled={saving || !form.name.trim()}>
            {saving ? "Guardando…" : "Guardar conector"}
          </Button>
        )}
      </div>
    </div>
  );
}
