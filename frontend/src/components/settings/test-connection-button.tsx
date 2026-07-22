"use client";

import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  label?: string;
};

export function TestConnectionButton({ onClick, loading, disabled, label = "Probar conexión" }: Props) {
  return (
    <Button variant="outline" onClick={onClick} disabled={disabled || loading}>
      <RefreshCw className={cnIcon(loading)} />
      {loading ? "Probando…" : label}
    </Button>
  );
}

function cnIcon(loading?: boolean) {
  return `mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`;
}
