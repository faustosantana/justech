"use client";

import { ArrowUp, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useAssistantContext } from "@/lib/assistant-context";
import { cn } from "@/lib/utils";

const PROMPTS = [
  { label: "Buscar cliente", query: "Buscar información de un cliente" },
  { label: "Generar cotización", query: "Ayúdame a generar una cotización" },
  { label: "Buscar licitación", query: "Buscar licitaciones relevantes" },
  { label: "Buscar documento", query: "Buscar un documento en el repositorio" },
  { label: "Consultar ERP", query: "Consultar datos en Odoo ERP" },
  { label: "Buscar proveedor", query: "Buscar proveedor o lista de precios" },
];

type Props = {
  suggestions?: string[];
  className?: string;
};

export function HomeAssistantPanel({ suggestions = [], className }: Props) {
  const { askAbout } = useAssistantContext();
  const [draft, setDraft] = useState("");

  const chips = suggestions.length > 0 ? suggestions.slice(0, 4).map((s) => ({ label: s, query: s })) : PROMPTS;

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const q = draft.trim();
    if (!q) return;
    askAbout(q);
    setDraft("");
  }

  return (
    <aside className={cn("home-glass flex h-full flex-col rounded-2xl p-5", className)}>
      <div className="mb-4 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold text-foreground">Asistente JAIOS</p>
          <p className="text-xs text-muted-foreground">¿Qué deseas hacer?</p>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
        {chips.map((item) => (
          <button
            key={item.label}
            type="button"
            onClick={() => askAbout(item.query)}
            className="rounded-xl px-3 py-2.5 text-left text-sm text-foreground/90 transition hover:bg-primary/8 hover:text-primary"
          >
            {item.label}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="mt-4 flex gap-2 border-t border-border/40 pt-4">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Escribe tu consulta…"
          className="home-glass-input flex-1 rounded-xl px-3 py-2.5 text-sm outline-none"
        />
        <button
          type="submit"
          disabled={!draft.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition hover:bg-primary/90 disabled:opacity-40"
          aria-label="Enviar"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>
    </aside>
  );
}
