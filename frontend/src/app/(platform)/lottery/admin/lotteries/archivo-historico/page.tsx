"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryAdmin } from "@/lib/lottery";
import { fetchArchivedLotteries, type ActiveLotteryItem } from "@/components/lottery/control-center/active-lotteries";

export default function ArchivoHistoricoLotteriesPage() {
  const router = useRouter();
  const [items, setItems] = useState<ActiveLotteryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      if (!getAccessToken()) {
        router.replace("/login?session=expired");
        return;
      }
      try {
        const access = await apiClient.getPlatformAccess().catch(() => null);
        const perms = access?.permissions ?? [];
        if (!canAccessLotteryAdmin(getUserRole(), perms)) {
          setError("Acceso denegado — solo administradores autorizados.");
          setLoading(false);
          return;
        }
        setItems(await fetchArchivedLotteries());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el archivo histórico");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  return (
    <AppShell
      title="Archivo histórico de loterías"
      description="Fuentes conservadas fuera del universo activo de análisis"
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Button asChild variant="outline" size="sm">
          <Link href="/lottery/admin/lotteries">Volver a loterías</Link>
        </Button>
      </div>
      <Card className="mb-4 border-amber-300 bg-amber-50 dark:bg-amber-950/30">
        <CardContent className="pt-6 text-sm">
          Esta fuente se conserva únicamente como histórico y no participa en los análisis,
          señales ni cálculos activos. Para incorporar una lotería al universo operativo, márquela
          como destacada de forma deliberada en Administración → Loterías.
        </CardContent>
      </Card>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {loading ? <p className="text-sm text-muted-foreground">Cargando…</p> : null}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Loterías archivadas ({items.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {items.map((l) => (
              <li key={l.id} className="rounded border p-2">
                <div className="font-medium">{l.name}</div>
                <div className="text-xs text-muted-foreground">Fuera del universo activo</div>
              </li>
            ))}
            {!loading && !items.length ? (
              <li className="text-muted-foreground">No hay loterías archivadas visibles.</li>
            ) : null}
          </ul>
        </CardContent>
      </Card>
    </AppShell>
  );
}
