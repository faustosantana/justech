"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Star } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryModule, DISCLAIMER, type LotteryFavorite } from "@/lib/lottery";

export default function LotteryFavoritesPage() {
  const router = useRouter();
  const [items, setItems] = useState<LotteryFavorite[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError("Sin permiso");
      return;
    }
    try {
      const res = await apiClient.listLotteryFavorites();
      setItems(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar favoritos");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const remove = async (lotteryId: string) => {
    await apiClient.removeLotteryFavorite(lotteryId);
    await load();
  };

  return (
    <AppShell title="Favoritos" description="Tus loterías marcadas">
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <Link href="/lottery" className="text-primary underline">
          Inicio
        </Link>
        <Link href="/lottery/lotteries" className="text-primary underline">
          Catálogo
        </Link>
        <Link href="/lottery/saved" className="text-primary underline">
          Guardadas
        </Link>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {items.length === 0 && !error && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Sin favoritos. Márcalos desde el catálogo de loterías.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {items.map((f) => (
          <Card key={f.lottery_id}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Star className="h-4 w-4 fill-amber-500 text-amber-500" aria-hidden />
                <Link className="hover:underline" href={`/lottery/lotteries/${f.lottery.slug}`}>
                  {f.lottery.name}
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button asChild size="sm">
                <Link href={`/lottery/search?lottery=${encodeURIComponent(f.lottery.name)}`}>
                  Consultar
                </Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href={`/lottery/chat?lottery=${encodeURIComponent(f.lottery.name)}`}>Chat</Link>
              </Button>
              <Button size="sm" variant="ghost" onClick={() => void remove(f.lottery_id)}>
                Quitar
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="mt-4 text-xs text-muted-foreground">{DISCLAIMER}</p>
    </AppShell>
  );
}
