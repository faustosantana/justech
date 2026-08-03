"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function PlatformError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[platform-error-boundary]", error?.digest || error?.message || error);
  }, [error]);

  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 p-6 text-center">
      <h2 className="text-lg font-semibold">No se pudo cargar esta sección</h2>
      <p className="max-w-md text-sm text-muted-foreground">
        Ocurrió un error al renderizar la página. Puede reintentar o volver al dashboard.
      </p>
      {error?.digest ? (
        <p className="text-xs text-muted-foreground">ID de incidente: {error.digest}</p>
      ) : null}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button type="button" onClick={() => reset()}>
          Reintentar
        </Button>
        <Button type="button" variant="outline" onClick={() => {
          window.location.href = "/dashboard";
        }}>
          Ir al dashboard
        </Button>
      </div>
    </div>
  );
}
