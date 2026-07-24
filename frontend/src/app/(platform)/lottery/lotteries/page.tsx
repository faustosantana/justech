"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, LineChart, Search, Star } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { lotteryDisplayName } from "@/lib/lottery-display-names";
import {
  canAccessLotteryModule,
  healthStatusLabel,
  type LotteryCatalogCard,
} from "@/lib/lottery";

const PAGE_SIZE = 100;

export default function LotteryCatalogPage() {
  const router = useRouter();
  const [items, setItems] = useState<LotteryCatalogCard[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

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
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryCatalog({
        q: q || undefined,
        featured_only: true,
        favorites_only: favoritesOnly || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar catálogo");
    } finally {
      setLoading(false);
    }
  }, [router, q, favoritesOnly, page]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleFav = async (card: LotteryCatalogCard) => {
    try {
      if (card.is_favorite) {
        await apiClient.removeLotteryFavorite(card.id);
      } else {
        await apiClient.addLotteryFavorite(card.id);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar favorito");
    }
  };

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  };

  return (
    <AppShell
      title="Catálogo de loterías"
      description="Solo las siete loterías activas del producto. El resto está en Archivo histórico."
    >
      <form onSubmit={submitSearch} className="mb-3 flex flex-wrap gap-2">
        <Input
          aria-label="Buscar lotería"
          placeholder="Buscar entre las siete activas…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="max-w-xs"
        />
        <Button type="submit" variant="outline" size="sm">
          <Search className="mr-1.5 h-3.5 w-3.5" />
          Buscar
        </Button>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={favoritesOnly}
            onChange={(e) => {
              setFavoritesOnly(e.target.checked);
              setPage(1);
            }}
          />
          Favoritas
        </label>
        <Button asChild variant="outline" size="sm">
          <Link href="/lottery">Inicio</Link>
        </Button>
      </form>

      <p className="mb-3 text-sm text-muted-foreground">
        {loading
          ? "Cargando…"
          : `${total.toLocaleString()} lotería(s) activas · página ${page} de ${totalPages}`}
      </p>

      {error && <p className="mb-3 text-sm text-destructive">{error}</p>}

      {!loading && items.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No hay loterías que coincidan con los filtros.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((card) => (
          <Card key={card.id}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-start justify-between gap-2 text-base">
                <Link className="hover:underline" href={`/lottery/lotteries/${card.slug}`}>
                  <span className="mr-1">{card.flag_emoji || "🏳️"}</span>
                  {lotteryDisplayName(card.id, card.commercial_name || card.name)}
                </Link>
                <button
                  type="button"
                  aria-label={card.is_favorite ? "Quitar favorito" : "Marcar favorito"}
                  onClick={() => void toggleFav(card)}
                  className="text-amber-500"
                >
                  <Star className={`h-4 w-4 ${card.is_favorite ? "fill-current" : ""}`} />
                </button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p>
                {card.country_code || card.country || "—"} · {card.timezone || "America/Santo_Domingo"}
                {card.draw_times ? ` · ${card.draw_times}` : ""}
              </p>
              {card.last_numbers.length > 0 ? (
                <p className="font-mono text-base font-semibold text-foreground">
                  {card.last_numbers.join(" · ")}
                </p>
              ) : (
                <p>Sin números recientes</p>
              )}
              <p>Último resultado: {card.last_draw_date || "—"}</p>
              <p>Última sync: {card.last_sync_at ? new Date(card.last_sync_at).toLocaleString("es-DO") : "—"}</p>
              <p>{card.draw_count.toLocaleString()} sorteos</p>
              <div className="flex flex-wrap gap-1.5">
                <Badge
                  variant={
                    card.health_status === "healthy"
                      ? "success"
                      : card.health_status === "error"
                        ? "danger"
                        : "muted"
                  }
                >
                  {healthStatusLabel(card.health_status)}
                </Badge>
                {card.is_sync_enabled && <Badge variant="outline">sync</Badge>}
                {card.is_ai_enabled && <Badge variant="outline">IA</Badge>}
                {card.is_featured && <Badge variant="warning">Destacada</Badge>}
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <Button asChild size="sm" variant="outline">
                  <Link href={`/lottery/lotteries/${card.slug}`}>Historial</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href={`/lottery/statistics?lottery=${encodeURIComponent(card.slug)}`}>
                    <LineChart className="mr-1 h-3 w-3" />
                    Stats
                  </Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href={`/lottery/chat?lottery=${encodeURIComponent(card.slug)}`}>IA</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href={`/lottery/search?lottery=${encodeURIComponent(card.name)}`}>
                    Consultar
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="h-4 w-4" />
            Anterior
          </Button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Siguiente
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </AppShell>
  );
}
