"use client";

import Link from "next/link";

import { cn } from "@/lib/utils";

type Props = {
  number: number | string;
  className?: string;
  size?: "sm" | "md" | "lg";
  title?: string;
};

/** Clickable lottery number → full analysis screen. */
export function LotteryNumberLink({ number, className, size = "md", title }: Props) {
  const n = String(number).replace(/\D/g, "");
  if (!n) return <span className={className}>—</span>;
  const href = `/lottery/analizar?number=${n}&auto=1`;
  const sizeCls =
    size === "lg"
      ? "min-h-14 min-w-14 text-2xl font-bold"
      : size === "sm"
        ? "min-h-8 min-w-8 text-sm font-semibold"
        : "min-h-10 min-w-10 text-base font-bold";
  return (
    <Link
      href={href}
      title={title || `Analizar el ${n}`}
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-blue-600 text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400",
        sizeCls,
        className,
      )}
    >
      {n.padStart(2, "0")}
    </Link>
  );
}
