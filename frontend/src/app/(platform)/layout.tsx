import type { ReactNode } from "react";

import { AssistantProvider } from "@/lib/assistant-context";
import { CompanyContextProvider } from "@/lib/company-context";

export default function PlatformLayout({ children }: { children: ReactNode }) {
  return (
    <CompanyContextProvider>
      <AssistantProvider>
        <div className="h-full platform-backdrop">{children}</div>
      </AssistantProvider>
    </CompanyContextProvider>
  );
}
