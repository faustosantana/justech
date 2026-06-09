"use client";

import { Send } from "lucide-react";
import { useState } from "react";

import { AssistantAvatar } from "@/components/assistant/assistant-avatar";
import { Button } from "@/components/ui/button";
import { useAssistantContext } from "@/lib/assistant-context";
import { cn } from "@/lib/utils";

interface AssistantPromptCardProps {
  message: string;
  suggestions?: string[];
  className?: string;
  compact?: boolean;
}

export function AssistantPromptCard({
  message,
  suggestions = [],
  className,
  compact = false,
}: AssistantPromptCardProps) {
  const { askAbout } = useAssistantContext();
  const [draft, setDraft] = useState("");

  function submit(value?: string) {
    const q = (value ?? draft).trim();
    if (!q) return;
    askAbout(q);
    setDraft("");
  }

  return (
    <section
      className={cn(
        "brand-surface-accent overflow-hidden",
        className,
      )}
    >
      <div className="brand-panel-header flex gap-4 p-5 md:p-6">
        <AssistantAvatar size={compact ? "md" : "xl"} state="attention" animated />
        <div className="min-w-0 flex-1 space-y-4">
          <div>
            <p className="brand-chip mb-1">JAIOS Assistant</p>
            <p className="mt-1 text-sm leading-relaxed text-foreground md:text-lg">{message}</p>
          </div>
          <div className="flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="Pregúntame algo de tu empresa…"
              className="brand-input min-w-0 flex-1"
            />
            <Button onClick={() => submit()} className="shrink-0 px-4">
              <Send className="h-4 w-4" />
            </Button>
          </div>
          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => submit(s)}
                  className="brand-chip cursor-pointer border-border/80 bg-background px-3 py-1.5 normal-case tracking-normal text-muted-foreground transition hover:border-primary/40 hover:text-primary"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
