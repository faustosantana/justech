"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api";
import type { PlatformAccess } from "@/lib/admin";

export function usePlatformAccess() {
  const [access, setAccess] = useState<PlatformAccess | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getPlatformAccess()
      .then(setAccess)
      .catch(() => setAccess(null))
      .finally(() => setLoading(false));
  }, []);

  return { access, loading };
}
