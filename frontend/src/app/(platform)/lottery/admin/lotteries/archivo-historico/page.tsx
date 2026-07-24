"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryAdmin, type LotteryAdminLottery } from "@/lib/lottery";

export default function ArchivoHistoricoLotteriesPage() {
  const router = useRouter();
  const [items, setItems] = useState<LotteryAdminLottery[]>([]);
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
        const rows = await apiClient.getLotteryAdminLotteries({
          featured: false,
          limit: 200,
          offset: 0,
        });
        setItems(rows);
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
          <Link href="/lottery/admin/lotteries">Volver a loterías activas</Link>
        </Button>
      </div>
      <Card className="mb-4 border-amber-300 bg-amber-50 dark:bg-amber-950/30">
        <CardContent className="pt-6 text-sm">
          Esta lotería se conserva únicamente como histórico y no participa en la experiencia ni en
          los análisis activos. No aparece en dashboard, catálogo, buscadores ni filtros ordinarios.
        </CardContent>
      </Card>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {loading ? <p className="text-sm text-muted-foreground">Cargando…</p> : null}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Loterías archivadas ({items.length})</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>ID</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Sorteos</TableHead>
                <TableHead>Último resultado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((l) => (
                <TableRow key={l.id}>
                  <TableCell className="font-medium">{l.commercial_name || l.name}</TableCell>
                  <TableCell className="font-mono text-xs">{l.id}</TableCell>
                  <TableCell>Archivada</TableCell>
                  <TableCell>{(l.draw_count ?? 0).toLocaleString()}</TableCell>
                  <TableCell>{l.last_draw_date || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {!loading && !items.length ? (
            <p className="mt-3 text-sm text-muted-foreground">No hay loterías archivadas.</p>
          ) : null}
        </CardContent>
      </Card>
    </AppShell>
  );
}
