"use client";

/** Evita mismatch de hidratación con `new Date()` en SSR. */
export function CopyrightYear() {
  return <span suppressHydrationWarning>{new Date().getFullYear()}</span>;
}
