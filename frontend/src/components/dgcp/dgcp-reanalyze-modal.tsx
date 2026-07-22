"use client";

import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Props = {
  open: boolean;
  processCode?: string;
  analyzedAt?: string | null;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function DgcpReanalyzeModal({
  open,
  processCode,
  analyzedAt,
  busy,
  onCancel,
  onConfirm,
}: Props) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dgcp-reanalyze-title"
    >
      <Card className="w-full max-w-md border-primary/30 shadow-lg">
        <CardHeader className="pb-2">
          <CardTitle id="dgcp-reanalyze-title" className="text-base flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-primary" />
            Reanalizar requisitos
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            {processCode ? (
              <>
                El expediente <strong className="text-foreground">{processCode}</strong> ya fue
                analizado
                {analyzedAt ? ` el ${analyzedAt}` : ""}. ¿Desea volver a leer los documentos y
                actualizar el checklist y las recomendaciones?
              </>
            ) : (
              <>
                Este expediente ya fue analizado. ¿Desea volver a leer los documentos y actualizar
                el checklist y las recomendaciones?
              </>
            )}
          </p>
          <p className="text-xs text-muted-foreground">
            El análisis anterior se conserva hasta que termine el nuevo. Puede seguir el progreso en
            la barra de estado.
          </p>
          <div className="flex flex-wrap gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onCancel} disabled={busy}>
              Cancelar
            </Button>
            <Button type="button" onClick={onConfirm} disabled={busy}>
              {busy ? "Iniciando…" : "Reanalizar"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
