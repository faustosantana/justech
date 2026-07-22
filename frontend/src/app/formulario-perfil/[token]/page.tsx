"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getApiUrl } from "@/lib/api";
import { RELATION_TYPES, type RepresentativeCreatePayload } from "@/lib/company-representatives";

const FORM_FIELDS: { key: string; label: string; required?: boolean }[] = [
  { key: "razon_social", label: "Razón social", required: true },
  { key: "rnc", label: "RNC", required: true },
  { key: "nombre_comercial", label: "Nombre comercial" },
  { key: "direccion", label: "Dirección fiscal", required: true },
  { key: "telefono", label: "Teléfono", required: true },
  { key: "correo", label: "Correo", required: true },
  { key: "registro_mercantil", label: "Registro mercantil", required: true },
  { key: "datos_bancarios", label: "Datos bancarios", required: true },
  { key: "proveedor_estado", label: "Proveedor del Estado (RPE)" },
];

type RepFormRow = RepresentativeCreatePayload & { id?: string };

const EMPTY_REP: RepFormRow = {
  full_name: "",
  identification_number: "",
  position: "",
  relation_type: "representante_legal",
  email: "",
  phone: "",
  can_sign: true,
  is_legal_representative: true,
  can_participate_in_bids: true,
};

export default function PublicProfileFormPage() {
  const params = useParams();
  const token = String(params.token ?? "");
  const [values, setValues] = useState<Record<string, string>>({});
  const [representatives, setRepresentatives] = useState<RepFormRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const baseUrl = `${getApiUrl()}/documents/public/profile-form/${token}`;

  useEffect(() => {
    document.title = "Actualización de perfil — JAIOS";
    if (!token) return;
    fetch(`${baseUrl}/representatives`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.representatives?.length) {
          setRepresentatives(
            data.representatives.map((rep: RepFormRow) => ({
              id: rep.id,
              full_name: rep.full_name,
              identification_number: rep.identification_number ?? "",
              position: rep.position ?? "",
              relation_type: rep.relation_type,
              email: rep.email ?? "",
              phone: rep.phone ?? "",
              can_sign: rep.can_sign,
              is_legal_representative: rep.is_legal_representative,
              can_participate_in_bids: rep.can_participate_in_bids,
            })),
          );
        }
      })
      .catch(() => undefined);
  }, [token, baseUrl]);

  const submit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(baseUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...values,
          representatives: representatives.filter((r) => r.full_name.trim().length > 0),
        }),
      });
      const data = (await res.json().catch(() => ({}))) as { detail?: string | { message?: string } };
      if (!res.ok) {
        const msg =
          typeof data.detail === "string"
            ? data.detail
            : typeof data.detail === "object" && data.detail?.message
              ? data.detail.message
              : "No se pudo guardar el formulario.";
        throw new Error(msg);
      }
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al enviar.");
    } finally {
      setLoading(false);
    }
  }, [baseUrl, values, representatives]);

  if (!token) {
    return (
      <div className="mx-auto max-w-lg p-8">
        <p className="text-red-600">Enlace inválido.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-xl space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Actualización de perfil empresarial</CardTitle>
            <p className="text-sm text-muted-foreground">
              Datos corporativos y representantes. Puede agregar varios representantes o firmantes.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {success ? (
              <p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">
                Información guardada correctamente. Puede cerrar esta ventana.
              </p>
            ) : (
              <>
                {FORM_FIELDS.map((field) => (
                  <label key={field.key} className="block text-sm">
                    <span className="font-medium">
                      {field.label}
                      {field.required ? " *" : ""}
                    </span>
                    <input
                      className="mt-1 w-full rounded-lg border px-3 py-2"
                      value={values[field.key] ?? ""}
                      onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                      required={field.required}
                    />
                  </label>
                ))}

                <div className="border-t pt-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="font-semibold">Representantes y firmantes</h2>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setRepresentatives((r) => [...r, { ...EMPTY_REP }])}
                    >
                      + Agregar representante
                    </Button>
                  </div>
                  {representatives.length === 0 ? (
                    <p className="rounded-lg border border-dashed bg-slate-50 px-3 py-4 text-sm text-muted-foreground">
                      No hay representantes registrados. Presione «+ Agregar representante» para incluir uno.
                    </p>
                  ) : (
                  representatives.map((rep, idx) => (
                    <div key={idx} className="mb-4 space-y-2 rounded-lg border bg-white p-3">
                      <Input
                        placeholder="Nombre completo *"
                        value={rep.full_name}
                        onChange={(e) => {
                          const next = [...representatives];
                          next[idx] = { ...rep, full_name: e.target.value };
                          setRepresentatives(next);
                        }}
                      />
                      <Input
                        placeholder="Cédula / Pasaporte"
                        value={rep.identification_number}
                        onChange={(e) => {
                          const next = [...representatives];
                          next[idx] = { ...rep, identification_number: e.target.value };
                          setRepresentatives(next);
                        }}
                      />
                      <Input
                        placeholder="Cargo"
                        value={rep.position}
                        onChange={(e) => {
                          const next = [...representatives];
                          next[idx] = { ...rep, position: e.target.value };
                          setRepresentatives(next);
                        }}
                      />
                      <select
                        className="w-full rounded-md border px-3 py-2 text-sm"
                        value={rep.relation_type}
                        onChange={(e) => {
                          const next = [...representatives];
                          next[idx] = { ...rep, relation_type: e.target.value };
                          setRepresentatives(next);
                        }}
                      >
                        {RELATION_TYPES.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                      {representatives.length > 1 && (
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => setRepresentatives((r) => r.filter((_, i) => i !== idx))}
                        >
                          Eliminar
                        </Button>
                      )}
                    </div>
                  ))
                  )}
                </div>

                {error && <p className="text-sm text-red-600">{error}</p>}
                <Button className="w-full" disabled={loading} onClick={() => void submit()}>
                  {loading ? "Guardando…" : "Guardar en JAIOS"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
