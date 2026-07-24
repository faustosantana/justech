export const NR_HISTORICAL_DISCLAIMER =
  "Este resultado es una señal histórica producida por el Motor de Relaciones Numéricas. No constituye garantía de resultado.";

export function NrDisclaimer({ className = "" }: { className?: string }) {
  return (
    <p
      className={`rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-950 dark:text-amber-100 ${className}`}
      role="note"
    >
      {NR_HISTORICAL_DISCLAIMER}
    </p>
  );
}
