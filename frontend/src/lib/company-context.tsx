"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api";
import type { GlobalCompanyContext } from "@/lib/company-context-types";

type CompanyContextValue = {
  context: GlobalCompanyContext | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setSelection: (payload: {
    selection_mode: "single" | "multi" | "all";
    active_company_id?: number;
    selected_company_ids?: number[];
  }) => Promise<void>;
  scopeLabel: string;
};

const CompanyContext = createContext<CompanyContextValue | null>(null);

export function CompanyContextProvider({ children }: { children: React.ReactNode }) {
  const [context, setContext] = useState<GlobalCompanyContext | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getCompanyContext();
      setContext(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setSelection = useCallback(
    async (payload: {
      selection_mode: "single" | "multi" | "all";
      active_company_id?: number;
      selected_company_ids?: number[];
    }) => {
      const data = await apiClient.setCompanyContext(payload);
      setContext(data);
    },
    [],
  );

  const value = useMemo(
    () => ({
      context,
      loading,
      refresh,
      setSelection,
      scopeLabel: context?.scope_label || "Sin empresa seleccionada",
    }),
    [context, loading, refresh, setSelection],
  );

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
}

export function useCompanyContext() {
  const ctx = useContext(CompanyContext);
  if (!ctx) {
    throw new Error("useCompanyContext must be used within CompanyContextProvider");
  }
  return ctx;
}
