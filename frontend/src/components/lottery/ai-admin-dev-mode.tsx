"use client";

import { createContext, useContext, useEffect, useState } from "react";

type DevModeCtx = {
  developerMode: boolean;
  setDeveloperMode: (v: boolean) => void;
};

const Ctx = createContext<DevModeCtx>({
  developerMode: false,
  setDeveloperMode: () => undefined,
});

export function LotteryAIDevModeProvider({ children }: { children: React.ReactNode }) {
  const [developerMode, setDeveloperMode] = useState(false);
  useEffect(() => {
    try {
      setDeveloperMode(localStorage.getItem("lottery_ai_dev_mode") === "1");
    } catch {
      /* ignore */
    }
  }, []);
  const set = (v: boolean) => {
    setDeveloperMode(v);
    try {
      localStorage.setItem("lottery_ai_dev_mode", v ? "1" : "0");
    } catch {
      /* ignore */
    }
  };
  return <Ctx.Provider value={{ developerMode, setDeveloperMode: set }}>{children}</Ctx.Provider>;
}

export function useLotteryAIDevMode() {
  return useContext(Ctx);
}
