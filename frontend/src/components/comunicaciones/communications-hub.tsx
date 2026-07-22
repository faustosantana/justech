"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Contacts360Panel } from "@/components/comunicaciones/contacts-360-panel";
import { CommunicationsUnifiedSearch } from "@/components/comunicaciones/communications-unified-search";
import { WhatsappInbox } from "@/components/comunicaciones/whatsapp-inbox";
import { M365Workspace } from "@/components/m365/m365-workspace";
import type { HubTab } from "@/lib/communications";

export function CommunicationsHub() {
  const searchParams = useSearchParams();
  const tabParam = (searchParams.get("tab") as HubTab) || "whatsapp";
  const qParam = searchParams.get("q") || "";
  const [tab, setTab] = useState<HubTab>(tabParam);

  useEffect(() => {
    setTab(tabParam);
  }, [tabParam]);

  const isWhatsapp = tab === "whatsapp";

  return (
    <div className="space-y-4">
      {!isWhatsapp && tab === "historial" && (
        <div className="max-w-md">
          <CommunicationsUnifiedSearch initialQuery={qParam} compact />
        </div>
      )}

      {isWhatsapp && <WhatsappInbox />}

      {tab === "outlook" && (
        <div className="-mx-2">
          <M365Workspace />
        </div>
      )}

      {tab === "teams" && (
        <div className="-mx-2">
          <M365Workspace />
        </div>
      )}

      {tab === "contactos" && <Contacts360Panel />}

      {tab === "historial" && (
        <div className="rounded-2xl border p-4">
          <CommunicationsUnifiedSearch initialQuery={qParam} />
        </div>
      )}
    </div>
  );
}
