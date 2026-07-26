"use client";

import Link from "next/link";

import { cn } from "@/lib/utils";

type Props = {
  number: number | string;
  className?: string;
  size?: "sm" | "md" | "lg";
  title?: string;
  lottery?: string | null;
  date?: string | null;
  position?: string | number | null;
  withNumber?: string | number | null;
};

/** Clickable lottery number → full analysis screen with optional draw context. */
export function LotteryNumberLink({
  number,
  className,
  size = "md",
  title,
  lottery,
  date,
  position,
  withNumber,
}: Props) {
  const n = String(number).replace(/\D/g, "");
  if (!n) return <span className={className}>—</span>;
  const params = new URLSearchParams();
  params.set("number", n);
  params.set("auto", "1");
  if (lottery) params.set("lottery", String(lottery));
  if (date) params.set("date", String(date));
  if (position != null && String(position) !== "") params.set("position", String(position));
  if (withNumber != null && String(withNumber).replace(/\D/g, "")) {
    params.set("with", String(withNumber).replace(/\D/g, ""));
  }
  const href = `/lottery/analizar?${params.toString()}`;
  const sizeCls =
    size === "lg"
      ? "min-h-14 min-w-14 text-2xl font-bold"
      : size === "sm"
        ? "min-h-8 min-w-8 text-sm font-semibold"
        : "min-h-10 min-w-10 text-base font-bold";
  return (
    <Link
      href={href}
      title={title || `Analizar número ${n.padStart(2, "0")}`}
      className={cn(
        "inline-flex cursor-pointer items-center justify-center rounded-full bg-blue-600 text-white shadow-sm transition hover:scale-105 hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400",
        sizeCls,
        className,
      )}
    >
      {n.padStart(2, "0")}
    </Link>
  );
}
