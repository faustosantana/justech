"use client";

import { TestConnectionButton } from "@/components/settings/test-connection-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function TestConnectionPanel({
  onTest,
  loading,
  message,
  error,
  preview,
  httpStatus,
}: {
  onTest: () => void;
  loading?: boolean;
  message?: string | null;
  error?: string | null;
  preview?: string | null;
  httpStatus?: number | null;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="text-base">Prueba de conexión</CardTitle>
        <TestConnectionButton onClick={onTest} loading={loading} />
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {error && <p className="text-destructive">{error}</p>}
        {message && !error && (
          <p className={httpStatus && httpStatus < 400 ? "text-success" : "text-amber-700"}>
            {message}
            {httpStatus != null && ` (HTTP ${httpStatus})`}
          </p>
        )}
        {preview && (
          <pre className="max-h-48 overflow-auto rounded-lg bg-muted p-3 text-xs">{preview}</pre>
        )}
      </CardContent>
    </Card>
  );
}
