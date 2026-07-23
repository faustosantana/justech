"use client";

/** Display helpers for Lottery AI Admin — never bare "—" without explanation. */

export function displayValue(
  value: unknown,
  empty = "Sin datos suficientes",
): string {
  if (value === null || value === undefined || value === "") return empty;
  if (typeof value === "number" && Number.isNaN(value)) return empty;
  return String(value);
}

export function MetricLine({
  label,
  value,
  empty = "Sin datos suficientes",
}: {
  label: string;
  value: unknown;
  empty?: string;
}) {
  const available = !(value === null || value === undefined || value === "" || value === "—");
  return (
    <p className="text-sm">
      <span className="text-muted-foreground">{label}: </span>
      <span className={available ? "font-medium" : "text-muted-foreground italic"}>
        {available ? String(value) : empty}
      </span>
    </p>
  );
}
