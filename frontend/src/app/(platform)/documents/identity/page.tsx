"use client";

import { Loader2, Stamp, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import {
  IDENTITY_STATUS_LABELS,
  type CorporateIdentityOverview,
} from "@/lib/corporate-identity";
import { cn } from "@/lib/utils";

const COMPANIES = [
  { key: "justech", label: "Justech SRL" },
  { key: "just_office", label: "Just Office SRL" },
  { key: "mf_plug_safe", label: "PlugSafe" },
  { key: "omni_solutions", label: "Omni Solutions SRL" },
];

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "text-xs px-2 py-0.5 rounded-full border",
        status === "disponible" && "border-success/40 text-success bg-success/10",
        status === "faltante" && "border-destructive/40 text-destructive bg-destructive/10",
        status === "requiere_revision" && "border-warning/40 text-warning bg-warning/10",
      )}
    >
      {IDENTITY_STATUS_LABELS[status] ?? status}
    </span>
  );
}

export default function CorporateIdentityPage() {
  const [overview, setOverview] = useState<CorporateIdentityOverview | null>(null);
  const [companyKey, setCompanyKey] = useState("justech");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getCorporateIdentity(companyKey);
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar identidad corporativa");
    } finally {
      setLoading(false);
    }
  }, [companyKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleUpload = async (type: "signature" | "stamp", file: File) => {
    setUploading(type);
    setError(null);
    try {
      if (type === "signature") {
        const res = await apiClient.uploadCorporateSignature(file);
        setSuccess(res.message);
      } else {
        const res = await apiClient.uploadCorporateStamp(companyKey, file);
        setSuccess(res.message);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al subir archivo");
    } finally {
      setUploading(null);
    }
  };

  return (
    <AppShell
      title="Identidad corporativa"
      description="Firma y sellos para PDFs finales de licitación — separado de documentos legales DGCP"
    >
      <div className="mb-4">
        <Link href="/documents" className="text-sm text-primary hover:underline">
          ← Documentos
        </Link>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {COMPANIES.map((c) => (
          <Button
            key={c.key}
            size="sm"
            variant={companyKey === c.key ? "default" : "outline"}
            onClick={() => setCompanyKey(c.key)}
          >
            {c.label}
          </Button>
        ))}
      </div>

      {error && <p className="text-sm text-destructive mb-3">{error}</p>}
      {success && <p className="text-sm text-success mb-3">{success}</p>}

      {loading ? (
        <p className="text-sm text-muted-foreground flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando…
        </p>
      ) : overview ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Stamp className="h-4 w-4" /> Firma — Fausto
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {overview.signature && (
                <>
                  <p className="font-medium">{overview.signature.filename}</p>
                  <StatusBadge status={overview.signature.status} />
                </>
              )}
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <Button size="sm" variant="outline" disabled={uploading === "signature"} asChild>
                  <span>
                    {uploading === "signature" ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <Upload className="h-3 w-3 mr-1" />
                    )}
                    Subir / reemplazar firma
                  </span>
                </Button>
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void handleUpload("signature", f);
                  }}
                />
              </label>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sello — {overview.active_company_label ?? companyKey}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {overview.stamp ? (
                <>
                  <p className="font-medium">{overview.stamp.filename}</p>
                  <StatusBadge status={overview.stamp.status} />
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Sin sello configurado para esta empresa</p>
              )}
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <Button size="sm" variant="outline" disabled={uploading === "stamp"} asChild>
                  <span>
                    {uploading === "stamp" ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <Upload className="h-3 w-3 mr-1" />
                    )}
                    Subir / reemplazar sello
                  </span>
                </Button>
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void handleUpload("stamp", f);
                  }}
                />
              </label>
            </CardContent>
          </Card>

          {overview.alerts.length > 0 && (
            <Card className="md:col-span-2 border-warning/30">
              <CardHeader>
                <CardTitle className="text-base">Alertas</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-1">
                  {overview.alerts.map((a) => (
                    <li key={a}>• {a}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Sellos registrados</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm divide-y">
                {overview.stamps.map((s) => (
                  <li key={s.filename} className="py-2 flex justify-between gap-2">
                    <span>
                      {s.company_label ?? s.company_key} — {s.filename}
                    </span>
                    <StatusBadge status={s.status} />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </AppShell>
  );
}
