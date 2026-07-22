"use client";

import { CheckCircle2, Cloud, File, Link2, Search, Upload } from "lucide-react";
import { useMemo, useState } from "react";

import { M365DocumentPicker } from "@/components/m365/m365-document-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { M365DocumentItem } from "@/lib/m365-documents";
import type { RepositoryBinding } from "@/lib/settings";

type HubActionResult = {
  message: string;
  filename?: string;
  linkMode: "link" | "import";
  indexed?: boolean;
};

export function DocumentsHubM365Panel({
  compact,
  bindings = [],
  onPersisted,
}: {
  compact?: boolean;
  bindings?: RepositoryBinding[];
  onPersisted?: () => void;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [bindingId, setBindingId] = useState<string>("");
  const [lastAction, setLastAction] = useState<HubActionResult | null>(null);

  const configuredBindings = useMemo(
    () => bindings.filter((b) => b.id && b.status !== "not_configured"),
    [bindings],
  );

  const selectedBinding = configuredBindings.find((b) => b.id === bindingId) ?? configuredBindings[0];
  const effectiveBindingId = selectedBinding?.id ?? "";

  const handleSuccess = (message: string, linkMode: "link" | "import", item?: M365DocumentItem, indexed?: boolean) => {
    setLastAction({
      message,
      filename: item?.name,
      linkMode,
      indexed,
    });
    onPersisted?.();
  };

  const openPicker = () => {
    if (!effectiveBindingId) return;
    setPickerOpen(true);
  };

  const bindingSelector = configuredBindings.length > 0 && (
    <div className="space-y-1">
      <label htmlFor="hub-m365-binding" className="text-xs font-medium text-muted-foreground">
        Repositorio destino
      </label>
      <select
        id="hub-m365-binding"
        className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        value={effectiveBindingId}
        onChange={(e) => setBindingId(e.target.value)}
      >
        {configuredBindings.map((b) => (
          <option key={b.id} value={b.id!}>
            {b.label || b.folder_key}
            {b.indexed_files ? ` (${b.indexed_files} archivos)` : ""}
          </option>
        ))}
      </select>
    </div>
  );

  const actionFeedback = lastAction && (
    <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
      <div>
        <p className="font-medium text-emerald-800">{lastAction.message}</p>
        {lastAction.filename && (
          <p className="mt-0.5 text-xs text-muted-foreground">
            {lastAction.linkMode === "import" ? "Importado e indexado" : "Vinculado e indexado"}:{" "}
            <span className="font-medium text-foreground">{lastAction.filename}</span>
          </p>
        )}
      </div>
    </div>
  );

  const picker = effectiveBindingId ? (
    <M365DocumentPicker
      open={pickerOpen}
      onClose={() => setPickerOpen(false)}
      entityId=""
      title="Buscar documento en Microsoft 365"
      mode="both"
      repositoryTarget={{
        bindingId: effectiveBindingId,
        bindingLabel: selectedBinding?.label || selectedBinding?.folder_key,
      }}
      onLinked={(message) => handleSuccess(message, "link")}
      onImported={(message) => handleSuccess(message, "import", undefined, true)}
    />
  ) : null;

  if (compact) {
    return (
      <>
        {bindingSelector}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-2 gap-2"
          disabled={!effectiveBindingId}
          onClick={openPicker}
        >
          <Cloud className="h-4 w-4 text-sky-600" />
          Buscar en Microsoft 365
        </Button>
        {!effectiveBindingId && (
          <p className="mt-2 text-xs text-amber-700">Configure al menos un repositorio OneDrive.</p>
        )}
        {actionFeedback}
        {picker}
      </>
    );
  }

  return (
    <Card className="mb-6 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Search className="h-4 w-4 text-primary" />
          Búsqueda Microsoft 365
        </CardTitle>
        <CardDescription>
          Vincule o importe documentos desde OneDrive/SharePoint al repositorio JAIOS. Los cambios persisten tras
          refrescar.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {bindingSelector}
        <div className="flex flex-wrap gap-2">
          <Button type="button" className="gap-2" disabled={!effectiveBindingId} onClick={openPicker}>
            <Cloud className="h-4 w-4" />
            Buscar en Microsoft 365
          </Button>
        </div>
        {!effectiveBindingId && (
          <p className="text-sm text-amber-700">
            No hay repositorios configurados. Sincronice carpetas Justech-AI en la sección inferior.
          </p>
        )}
        {effectiveBindingId && (
          <p className="text-xs text-muted-foreground">
            En el picker use <Link2 className="inline h-3 w-3" /> Vincular (referencia M365) o{" "}
            <Upload className="inline h-3 w-3" /> Importar (copia + indexación en JAIOS).
          </p>
        )}
        {actionFeedback}
        {lastAction?.filename && (
          <div className="flex items-start gap-3 rounded-lg border bg-background p-3">
            <File className="mt-0.5 h-5 w-5 shrink-0 text-sky-600" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{lastAction.filename}</p>
              <p className="text-xs text-muted-foreground">
                Repositorio: {selectedBinding?.label || selectedBinding?.folder_key}
              </p>
            </div>
          </div>
        )}
      </CardContent>
      {picker}
    </Card>
  );
}
