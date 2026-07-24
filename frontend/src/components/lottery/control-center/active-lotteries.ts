/**
 * J-10L — Cliente del universo activo (is_featured).
 * No hardcodea nombres; la fuente de verdad es el backend.
 */

import { apiClient } from "@/lib/api";
import type { LotOption } from "@/components/lottery/control-center/motor-types";

export type ActiveLotteryItem = LotOption & {
  analysis_scope?: string;
  slug?: string;
};

export async function fetchActiveAnalysisLotteries(): Promise<{
  items: ActiveLotteryItem[];
  count: number;
  user_note?: string;
}> {
  const res = await apiClient.getLotteryNumericRelationsLotteries({ scope: "active" });
  return {
    items: (res.items || []) as ActiveLotteryItem[],
    count: Number(res.count ?? res.items?.length ?? 0),
    user_note: res.user_note,
  };
}

export async function fetchArchivedLotteries(): Promise<ActiveLotteryItem[]> {
  const res = await apiClient.getLotteryNumericRelationsLotteries({ scope: "archived" });
  return (res.items || []) as ActiveLotteryItem[];
}

/** “Todas” = las activas, nunca el inventario completo de la DB. */
export function selectAllActiveIds(items: { id: string }[]): string[] {
  return items.map((x) => x.id);
}
