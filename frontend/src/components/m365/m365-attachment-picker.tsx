"use client";

import { M365DocumentPicker } from "@/components/m365/m365-document-picker";
import type { M365DocumentItem } from "@/lib/m365-documents";

export interface PickedAttachment {
  name: string;
  onedrive_item_id: string;
  source_url?: string;
}

function toPickedAttachment(item: M365DocumentItem): PickedAttachment {
  return {
    name: item.name,
    onedrive_item_id: item.item_id || item.id,
    source_url: item.web_url || item.download_url || undefined,
  };
}

/** @deprecated Use M365DocumentPicker directly — wrapper de compatibilidad. */
export function M365AttachmentPicker({
  open,
  onClose,
  onPick,
}: {
  open: boolean;
  onClose: () => void;
  onPick: (item: PickedAttachment) => void;
  accountId?: string | null;
}) {
  return (
    <M365DocumentPicker
      open={open}
      onClose={onClose}
      entityId=""
      title="Adjuntar desde Microsoft 365"
      attachMode={{
        label: "Seleccionar",
        onAttach: (item) => {
          onPick(toPickedAttachment(item));
          onClose();
        },
      }}
    />
  );
}
