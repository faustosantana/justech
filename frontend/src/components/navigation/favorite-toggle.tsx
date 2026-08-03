"use client";

import { Star } from "lucide-react";

import { cn } from "@/lib/utils";

export function FavoriteToggle({
  appId,
  favorited,
  onToggle,
}: {
  appId: string;
  favorited: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onToggle(appId);
      }}
      className="absolute right-2 top-2 rounded-full p-1 text-muted-foreground/50 transition hover:text-amber-500"
      aria-label={favorited ? "Quitar de favoritos" : "Agregar a favoritos"}
    >
      <Star className={cn("h-3.5 w-3.5", favorited && "fill-amber-400 text-amber-500")} />
    </button>
  );
}
