"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export interface AssistantContextValue {
  companyContextId?: number | null;
  recordType?: string | null;
  recordId?: string | null;
  presetQuestion?: string | null;
}

interface AssistantContextState extends AssistantContextValue {
  setContext: (ctx: AssistantContextValue) => void;
  clearContext: () => void;
  clearRecordContext: () => void;
  askAbout: (question: string) => void;
  copilotOpen: boolean;
  proactiveMessage: string | null;
  openCopilot: (message?: string) => void;
  closeCopilot: () => void;
}

const Ctx = createContext<AssistantContextState | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [ctx, setCtx] = useState<AssistantContextValue>({});
  const [presetQuestion, setPresetQuestion] = useState<string | null>(null);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [proactiveMessage, setProactiveMessage] = useState<string | null>(null);

  const setContext = useCallback((c: AssistantContextValue) => {
    setCtx((prev) => ({ ...prev, ...c }));
  }, []);

  const clearContext = useCallback(() => {
    setCtx({});
  }, []);

  const clearRecordContext = useCallback(() => {
    setCtx((prev) => ({
      ...prev,
      recordType: null,
      recordId: null,
    }));
  }, []);

  const askAbout = useCallback((q: string) => {
    setPresetQuestion(q);
    setCopilotOpen(true);
    setTimeout(() => setPresetQuestion(null), 500);
  }, []);

  const openCopilot = useCallback((message?: string) => {
    if (message) setProactiveMessage(message);
    setCopilotOpen(true);
  }, []);

  const closeCopilot = useCallback(() => {
    setCopilotOpen(false);
  }, []);

  const value = useMemo(
    () => ({
      ...ctx,
      presetQuestion,
      setContext,
      clearContext,
      clearRecordContext,
      askAbout,
      copilotOpen,
      proactiveMessage,
      openCopilot,
      closeCopilot,
    }),
    [
      ctx,
      presetQuestion,
      setContext,
      clearContext,
      clearRecordContext,
      askAbout,
      copilotOpen,
      proactiveMessage,
      openCopilot,
      closeCopilot,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAssistantContext() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAssistantContext requires AssistantProvider");
  return v;
}
