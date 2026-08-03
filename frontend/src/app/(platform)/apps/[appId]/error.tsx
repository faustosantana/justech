"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function AppModuleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[apps-error-boundary]", error?.digest || error?.message || error);
  }, [error]);

  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 p-6 text-center">
      <h2 className="text-lg font-semibold">Error en el módulo</h2>
      <p className="max-w-md text-sm text-muted-foreground">
        Esta sección no pudo cargarse. Reintente o vuelva al listado del módulo.
      </p>
      {error?.digest ? (
        <p className="text-xs text-muted-foreground">ID de incidente: {error.digest}</p>
      ) : null}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button type="button" onClick={() => reset()}>
          Reintentar
        </Button>
        <Button type="button" variant="outline" onClick={() => {
          window.history.back();
        }}>
          Volver
        </Button>
      </div>
    </div>
  );
}
