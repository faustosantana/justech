"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  /** Si true, registra atajo global Cmd/Ctrl+K */
  registerShortcut?: boolean;
};

export function SpotlightSearch({ className, registerShortcut = true }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const goSearch = useCallback(
    (q: string) => {
      const trimmed = q.trim();
      if (trimmed.length < 2) return;
      setOpen(false);
      setQuery("");
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    },
    [router],
  );

  useEffect(() => {
    if (!registerShortcut) return;
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
        setTimeout(() => inputRef.current?.focus(), 50);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [registerShortcut]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    goSearch(query);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
          setTimeout(() => inputRef.current?.focus(), 50);
        }}
        className={cn(
          "home-glass group flex w-full max-w-2xl items-center gap-3 rounded-2xl px-4 py-3.5 text-left transition hover:shadow-md",
          className,
        )}
      >
        <Search className="h-5 w-5 shrink-0 text-muted-foreground transition group-hover:text-primary" />
        <span className="flex-1 text-sm text-muted-foreground">Buscar en JAIOS…</span>
        <kbd className="hidden rounded-lg border border-border/80 bg-background/60 px-2 py-0.5 text-[10px] font-medium text-muted-foreground sm:inline">
          ⌘K
        </kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[100] flex items-start justify-center bg-black/25 p-4 pt-[12vh] backdrop-blur-sm"
          onClick={() => setOpen(false)}
          role="presentation"
        >
          <form
            onSubmit={handleSubmit}
            onClick={(e) => e.stopPropagation()}
            className="home-glass w-full max-w-xl overflow-hidden rounded-2xl shadow-2xl"
          >
            <div className="flex items-center gap-3 border-b border-border/50 px-4 py-3">
              <Search className="h-5 w-5 text-primary" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Clientes, conversaciones, documentos, licitaciones…"
                className="flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
                autoFocus
              />
              <kbd className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">ESC</kbd>
            </div>
            <div className="px-4 py-3 text-xs text-muted-foreground">
              Busca clientes, conversaciones, correos, documentos, licitaciones, facturas, cotizaciones y proveedores.
            </div>
          </form>
        </div>
      )}
    </>
  );
}
