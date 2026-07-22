"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Star } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryModule, type LotteryLottery } from "@/lib/lottery";

export default function LotteryCatalogPage() {
  const router = useRouter();
  const [items, setItems] = useState<LotteryLottery[]>([]);
  const [favIds, setFavIds] = useState<Set<string>>(new Set());
  const [q, setQ] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError("Sin permiso");
      setLoading(false);
      return;
    }
    try {
      const [list, favs] = await Promise.all([
        apiClient.getLotteryLotteries(100, 0),
        apiClient.listLotteryFavorites().catch(() => ({ items: [] })),
      ]);
      setItems(list.items);
      setFavIds(new Set(favs.items.map((f) => f.lottery_id)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar catálogo");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    return items
      .filter((l) => (activeOnly ? l.active : true))
      .filter(
        (l) =>
          !term ||
          l.name.toLowerCase().includes(term) ||
          l.slug.toLowerCase().includes(term) ||
          String(l.source_id).includes(term),
      )
      .sort((a, b) => {
        const af = favIds.has(a.id) ? 0 : 1;
        const bf = favIds.has(b.id) ? 0 : 1;
        if (af !== bf) return af - bf;
        return a.name.localeCompare(b.name, "es");
      });
  }, [items, q, activeOnly, favIds]);

  const toggleFav = async (lot: LotteryLottery) => {
    try {
      if (favIds.has(lot.id)) {
        await apiClient.removeLotteryFavorite(lot.id);
        setFavIds((prev) => {
          const n = new Set(prev);
          n.delete(lot.id);
          return n;
        });
      } else {
        await apiClient.addLotteryFavorite(lot.id);
        setFavIds((prev) => new Set(prev).add(lot.id));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar favorito");
    }
  };

  return (
    <AppShell title="Catálogo de loterías" description="50 loterías del histórico importado">
      <div className="mb-3 flex flex-wrap gap-2">
        <Input
          aria-label="Buscar lotería"
          placeholder="Buscar por nombre o alias…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
          />
          Solo activas
        </label>
        <Button asChild variant="outline">
          <Link href="/lottery">Inicio</Link>
        </Button>
      </div>
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((lot) => (
          <Card key={lot.id}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-start justify-between gap-2 text-base">
                <Link className="hover:underline" href={`/lottery/lotteries/${lot.slug}`}>
                  {lot.name}
                </Link>
                <button
                  type="button"
                  aria-label={favIds.has(lot.id) ? "Quitar favorito" : "Marcar favorito"}
                  onClick={() => void toggleFav(lot)}
                  className="text-amber-500"
                >
                  <Star className={`h-4 w-4 ${favIds.has(lot.id) ? "fill-current" : ""}`} />
                </button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-xs text-muted-foreground">
              <p>
                {lot.first_draw_date || "—"} → {lot.last_draw_date || "—"}
              </p>
              <p>{lot.draw_count.toLocaleString()} sorteos · {lot.active ? "activa" : "inactiva"}</p>
              <div className="flex flex-wrap gap-2 pt-2">
                <Button asChild size="sm" variant="outline">
                  <Link href={`/lottery/search?lottery=${encodeURIComponent(lot.name)}`}>Consultar</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href={`/lottery/chat`}>Chat</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
